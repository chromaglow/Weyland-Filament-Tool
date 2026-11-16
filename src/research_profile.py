"""Research and import command.

  python -m src.research_profile research --material "<name>" \
      --source manufacturer=<url> --source community=<owner/repo:path|raw url> \
      [--source import=<profile.json>] --out <dir> [--offline] [--install]
  python -m src.research_profile import <profile.json> \
      [--merge-with manufacturer=<url> | community=<...> | import=<file>] --out <dir> [--install]

Collects settings from the sources, merges them (precedence per
docs/design/research-merge-spec.md), and writes preset files plus a sources
report to --out. Nothing is installed unless --install is given; then the
existing installer (src/install_profile.py) is used for the filament preset
and, when there are process values, the process preset.
"""
from __future__ import annotations

import argparse
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence

from src.data.merge import MergeConfig
from src.data.sourced import CollectedSettings
from src.generator.merged_export import KeyCheckError, export_merged
from src.importers.profile_import import UNKNOWN_KEYS_WARNING, ImportRejected, ImportResult, import_profile
from src.install_profile import install_profile
from src.scrapers.http_client import FetchError, PoliteFetcher, default_cache_dir
from src.scrapers.source_community_profiles import collect_profile, github_transport
from src.scrapers.source_manufacturer import collect_from_url
from src.utils.bambu_studio import BambuStudioIntegration, get_bambu_integration

MAX_CONTESTED_LINES = 10


class UsageError(Exception):
    pass


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "material"


class _BambuAt(BambuStudioIntegration):
    """Bambu Studio user folders under an explicit base dir (tests, dry runs)."""

    def __init__(self, root: Path, running: Optional[Callable[[], bool]] = None):
        self.bambu_studio_path = root
        self.device_ids = self._find_device_ids()
        self._running = running

    def is_bambu_studio_running(self) -> bool:
        return self._running() if self._running else super().is_bambu_studio_running()


def _parse_source(text: str) -> tuple:
    kind, sep, value = text.partition("=")
    if not sep or kind not in ("manufacturer", "community", "import") or not value:
        raise UsageError(f"bad source '{text}': use manufacturer=<url>, community=<repo:path or url> or import=<file>")
    return kind, value


def _gather(sources: Sequence[tuple], collected: CollectedSettings, *, offline, cache_dir, transport,
            min_interval, now, system_dirs) -> Dict[str, object]:
    """Add every source's values to `collected`; return info for the summary."""
    info: Dict[str, object] = {"unmapped": [], "import_notes": []}
    opts = {"cache_dir": cache_dir, "offline": offline}
    if min_interval is not None:
        opts["min_interval"] = min_interval
    for kind, value in sources:
        if kind == "manufacturer":
            res = collect_from_url(value, PoliteFetcher(transport=transport, **opts), retrieved_at=now,
                                   material_id=collected.material_id)
            collected.values.extend(res.settings.values)
            info["unmapped"] = list(info["unmapped"]) + list(res.unmapped)
        elif kind == "community":
            fetcher = PoliteFetcher(transport=transport or github_transport(), **opts)
            collected.values.extend(collect_profile(fetcher, value, retrieved_at=now).settings.values)
        else:
            imp = import_profile(value, system_dirs=system_dirs, retrieved_at=now)
            collected.values.extend(imp.collected.values)
            info["import_notes"] = list(info["import_notes"]) + _import_notes(imp)
    return info


def _import_notes(imp: ImportResult) -> List[str]:
    """One line per thing an imported file supplied that did not become a setting."""
    name = Path(imp.path).name
    notes = [f"{name}: key '{k}' not emitted (not a Bambu filament key or not a single value); raw {v!r}"
             for k, v in sorted(imp.extras.items())]
    notes += [f"{name}: {w}" for w in imp.warnings if not w.startswith(UNKNOWN_KEYS_WARNING)]
    return notes


MAX_DEFAULT_LINES = 8
_PRINT_RELEVANT = ("temp", "bed", "flow", "fan", "cooling", "volumetric")


def _default_rank(d) -> tuple:
    """Print-relevant keys (temperatures, bed, flow, cooling) first, then alphabetical."""
    return (not any(w in d.key for w in _PRINT_RELEVANT), d.key)


def _summarise(say, result, info, out_dir: Path) -> None:
    merged = result.merge_result
    say(f"Wrote to {out_dir}:")
    for p in (result.filament_path, result.process_path, result.collected_path, result.report_path):
        if p:
            say(f"  {p.name}")
    contested = [v for v in merged.all_values() if v.losers]
    say(f"Contested settings: {len(contested)}")
    for v in contested[:MAX_CONTESTED_LINES]:
        beaten = ", ".join(sorted({f"{x.source_id} ({x.raw})" for x in v.losers}))
        say(f"  {v.key} = {v.value} from {v.winner.source_id}; over {beaten}")
    if len(contested) > MAX_CONTESTED_LINES:
        say(f"  ... {len(contested) - MAX_CONTESTED_LINES} more in the report")
    defaults = result.template_defaults
    say(f"Assumptions: {len(merged.assumptions) + len(defaults)}")
    for a in merged.assumptions:
        say(f"  {a.key} = {a.value} ({a.winner.note or 'assumed'})")
    shown = sorted(defaults, key=_default_rank)[:MAX_DEFAULT_LINES]
    for d in shown:
        say(f"  {d.key} = {d.value} (template default, {d.template})")
    if len(defaults) > len(shown):
        say(f"  ... {len(defaults) - len(shown)} more template defaults in the report")
    notes = info["import_notes"]
    if notes:
        say(f"{len(notes)} imported file notes (not emitted or warnings); listed in {result.report_path.name}:")
        for line in notes[:MAX_CONTESTED_LINES]:
            say(f"  {line}")
        if len(notes) > MAX_CONTESTED_LINES:
            say(f"  ... {len(notes) - MAX_CONTESTED_LINES} more in the report")
    n = len(info["unmapped"])
    if n:
        say(f"{n} page items were not mapped to a setting; listed in {result.report_path.name}.")


def _append_unmapped(report: Path, unmapped: List[str], import_notes: Sequence[str] = ()) -> None:
    lines: List[str] = []
    if import_notes:
        lines += ["", "## Imported file notes", "",
                  "Keys and warnings from imported files that did not become settings:", ""]
        lines += [f"- {n}" for n in import_notes]
    if unmapped:
        lines += ["", "## Unmapped page items", "",
                  "Numbered items on the manufacturer page that were not turned into settings:", ""]
        lines += [f"- {u}" for u in unmapped]
    if not lines:
        return
    with open(report, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def _install(result, bambu, ask, say) -> int:
    code = install_profile(result.filament_path, bambu, ask=ask, say=say, kind="filament")
    if code == 0 and result.process_path:
        code = install_profile(result.process_path, bambu, ask=ask, say=say, kind="process")
    return code


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m src.research_profile")
    sub = p.add_subparsers(dest="command", required=True)

    def common(sp):
        sp.add_argument("--out", required=True, help="output folder")
        sp.add_argument("--name", help="preset name (default: material name or imported name)")
        sp.add_argument("--manufacturer", default="Generic", help="filament vendor for the preset")
        sp.add_argument("--material-type", default="pla")
        sp.add_argument("--offline", action="store_true", help="use cached responses only")
        sp.add_argument("--cache-dir", help="HTTP cache folder (default: user cache dir)")
        sp.add_argument("--install", action="store_true",
                        help="also install into Bambu Studio (off by default)")
        sp.add_argument("--bambu-dir", help="Bambu Studio base folder (default: auto-detect)")

    r = sub.add_parser("research", help="collect from online sources, merge, export")
    r.add_argument("--material", required=True)
    r.add_argument("--source", action="append", default=[], metavar="KIND=VALUE")
    common(r)
    i = sub.add_parser("import", help="read an existing profile file and export it")
    i.add_argument("file")
    i.add_argument("--merge-with", action="append", default=[], metavar="KIND=VALUE")
    common(i)
    return p


def main(argv: Optional[Sequence[str]] = None, *, transport=None, say: Callable[[str], None] = print,
         ask: Callable[[str], str] = input, running: Optional[Callable[[], bool]] = None,
         now: Optional[str] = None, min_interval: Optional[float] = None,
         system_dirs: Optional[list] = None) -> int:
    args = _build_parser().parse_args(sys.argv[1:] if argv is None else list(argv))
    now = now or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cache_dir = Path(args.cache_dir) if args.cache_dir else default_cache_dir()
    try:
        if args.command == "research":
            sources = [_parse_source(s) for s in args.source]
            if len(sources) < 2:
                raise UsageError("research needs at least two sources (e.g. manufacturer=<url> and community=<repo:path>)")
            name = args.name or args.material
            collected = CollectedSettings(material_id=_slug(args.material), name=name)
        else:
            sources = [("import", args.file)] + [_parse_source(s) for s in args.merge_with]
            first = import_profile(args.file, system_dirs=system_dirs, retrieved_at=now).collected
            name = args.name or first.name
            collected = CollectedSettings(material_id=_slug(name), name=name)
        info = _gather(sources, collected, offline=args.offline, cache_dir=cache_dir, transport=transport,
                       min_interval=min_interval, now=now, system_dirs=system_dirs)
        result = export_merged(collected, args.out, name=name, manufacturer=args.manufacturer,
                               material_type=args.material_type, config=MergeConfig(), generated_at=now)
    except UsageError as e:
        say(f"Error: {e}")
        return 2
    except KeyCheckError as e:
        say("Error: preset failed the key check, nothing written: "
            + "; ".join(f"{k}: {', '.join(v)}" for k, v in e.problems.items()))
        return 1
    except ImportRejected as e:
        say(f"Error: cannot import: {e}")
        return 1
    except FetchError as e:
        say(f"Error: {_fetch_message(e)}")
        return 1
    except OSError as e:
        say(f"Error: {e}")
        return 1

    _append_unmapped(result.report_path, list(info["unmapped"]), list(info["import_notes"]))
    _summarise(say, result, info, Path(args.out))
    if args.install:
        bambu = _BambuAt(Path(args.bambu_dir), running) if args.bambu_dir else get_bambu_integration()
        return _install(result, bambu, ask, say)
    return 0


def _fetch_message(e: FetchError) -> str:
    text = " ".join(str(e).split())
    kind = type(e).__name__
    if kind == "RobotsDisallowedError":
        return f"robots.txt does not allow fetching this page ({text}); not fetched."
    if kind == "OfflineCacheMissError":
        return f"offline mode and not in the cache ({text}); run once without --offline first."
    if kind == "RateLimitError":
        return f"rate limit reached ({text}); try again later."
    return text


if __name__ == "__main__":
    # the per-item "unmapped" warnings go to the report instead of the console
    logging.getLogger("src.scrapers.source_manufacturer").setLevel(logging.ERROR)
    sys.exit(main())
