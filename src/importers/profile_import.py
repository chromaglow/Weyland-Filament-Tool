"""Import Bambu Studio / OrcaSlicer filament presets and collected-settings JSON.

Imported files are data, never instructions: values are only parsed and stored.
Output values are SourcedValue with status "imported" and kind IMPORTED_PROFILE
(the collected-settings JSON keeps the statuses it already carries).

`inherits` is resolved read-only against system filament preset folders when
found; otherwise the parent is listed in ImportResult.unresolved_inherits.
Nothing is ever written to any Bambu Studio folder.
(Note: src/scrapers/source_community_profiles.py has its own inherits-chain
resolver for remote files; this one is intentionally separate.)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

from src.data.sourced import CollectedSettings, SourcedValue, SourceKind
from src.generator.bambu_keys import load_catalogue

PathLike = Union[str, Path]
MAX_INHERIT_DEPTH = 10

# Identity/bookkeeping keys: kept in ImportResult.meta, not emitted as values.
META_KEYS = frozenset({
    "name", "inherits", "from", "type", "setting_id", "filament_id", "version",
    "instantiation", "filament_settings_id", "compatible_printers",
    "compatible_printers_condition", "compatible_prints", "compatible_prints_condition",
})


class ImportRejected(ValueError):
    """The file is not an importable filament preset."""


@dataclass
class ImportResult:
    collected: CollectedSettings
    format: str  # "bambu_filament" | "collected_settings"
    path: str
    meta: Dict[str, Any] = field(default_factory=dict)
    extras: Dict[str, Any] = field(default_factory=dict)  # raw unknown / multi-value entries
    nil_keys: List[str] = field(default_factory=list)
    unresolved_inherits: List[str] = field(default_factory=list)
    resolved_inherits: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def find_system_filament_dirs() -> List[Path]:
    """Read-only discovery of local Bambu Studio system filament folders."""
    from src.utils.bambu_studio import BambuStudioIntegration

    dirs: List[Path] = []
    root = BambuStudioIntegration().bambu_studio_path
    if root:
        dirs.append(root / "system" / "BBL" / "filament")
    dirs.append(Path("C:/Program Files/Bambu Studio/resources/profiles/BBL/filament"))
    return [d for d in dirs if d.is_dir()]


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise ImportRejected(f"{path.name}: not readable JSON ({e})") from e
    if not isinstance(data, dict):
        raise ImportRejected(f"{path.name}: expected a JSON object")
    return data


def _scalar(text: str) -> Any:
    for conv in (int, float):
        try:
            return conv(text)
        except ValueError:
            pass
    return text


def _is_nil(v: Any) -> bool:
    return v == "nil" or (isinstance(v, list) and len(v) > 0 and all(x == "nil" for x in v))


def _find_parent(name: str, dirs: Sequence[Path]) -> Optional[Path]:
    for d in dirs:
        direct = d / f"{name}.json"
        if direct.is_file():
            return direct
        if d.is_dir():
            for hit in d.rglob(f"{name}.json"):
                return hit
    return None


def _flatten(path: Path, data: Dict[str, Any], dirs: Sequence[Path], res: ImportResult,
             seen: List[str]) -> Dict[str, tuple]:
    """Return key -> (raw value, file) with the child winning over its parents."""
    merged: Dict[str, tuple] = {}
    parent_name = data.get("inherits")
    if isinstance(parent_name, str) and parent_name:
        if parent_name in seen:
            res.warnings.append(f"inherits cycle at '{parent_name}'; chain stopped")
        elif len(seen) >= MAX_INHERIT_DEPTH:
            res.warnings.append(f"inherits chain deeper than {MAX_INHERIT_DEPTH}; stopped at '{parent_name}'")
        else:
            parent_path = _find_parent(parent_name, dirs)
            if parent_path is None:
                res.unresolved_inherits.append(parent_name)
                res.warnings.append(f"inherits '{parent_name}' not found in system presets; its values are missing")
            else:
                try:
                    parent = _load_json(parent_path)
                except ImportRejected as e:
                    res.unresolved_inherits.append(parent_name)
                    res.warnings.append(str(e))
                else:
                    res.resolved_inherits.append(parent_name)
                    merged.update(_flatten(parent_path, parent, dirs, res, seen + [parent_name]))
    for k, v in data.items():
        merged[k] = (v, path)
    return merged


def _import_bambu(path: Path, data: Dict[str, Any], dirs: Sequence[Path], now: str) -> ImportResult:
    kind = data.get("type")
    if kind is not None and kind != "filament":
        raise ImportRejected(f"{path.name}: this is a {kind} preset, only filament presets can be imported")
    name = data.get("name")
    cs = CollectedSettings(material_id=str(name) if name else path.stem, name=str(name) if name else path.stem)
    res = ImportResult(collected=cs, format="bambu_filament", path=str(path))
    filament_keys = set(load_catalogue()["filament"])
    flat = _flatten(path, data, dirs, res, [str(name)] if name else [])
    unknown: List[str] = []
    for key, (raw, src) in flat.items():
        if key in META_KEYS:
            if src == path:
                res.meta[key] = raw
            continue
        if _is_nil(raw):
            res.nil_keys.append(key)
            continue
        if key not in filament_keys:
            if src == path:
                res.extras[key] = raw
                unknown.append(key)
            continue
        value = raw
        if isinstance(raw, list):
            if len(raw) != 1:
                res.extras[key] = raw  # multi-value array: keep verbatim
                continue
            value = raw[0]
        if isinstance(value, str):
            value = _scalar(value)
        elif not isinstance(value, (int, float, bool)):
            res.extras[key] = raw
            continue
        cs.add(SourcedValue(
            key=key, value=value, source_id=f"imported:{src.name}",
            source_kind=SourceKind.IMPORTED_PROFILE, source_url=str(src),
            status="imported", retrieved_at=now, raw=json.dumps(raw),
        ))
    if unknown:
        res.warnings.append("unknown filament keys kept as raw extras: " + ", ".join(sorted(unknown)))
    return res


def _import_collected(path: Path, data: Dict[str, Any], material_id: Optional[str]) -> ImportResult:
    mats = data["materials"]
    ids = [m.get("id") for m in (mats.values() if isinstance(mats, dict) else mats)]
    if material_id is None:
        if len(ids) != 1:
            raise ImportRejected(f"{path.name}: pass material_id, file has materials {ids}")
        material_id = ids[0]
    cs = CollectedSettings.from_collected_file(path, material_id)
    return ImportResult(collected=cs, format="collected_settings", path=str(path))


def import_profile(path: PathLike, material_id: Optional[str] = None,
                   system_dirs: Optional[Sequence[PathLike]] = None,
                   retrieved_at: Optional[str] = None) -> ImportResult:
    """Import a Bambu/Orca filament preset or a collected-settings JSON.

    system_dirs: folders searched (read-only) for `inherits` parents; None
    discovers local Bambu Studio folders, [] disables resolution.
    material_id only matters for collected-settings files with several materials.
    Raises ImportRejected for process/machine presets and non-preset files.
    """
    p = Path(path)
    data = _load_json(p)
    if "materials" in data:
        return _import_collected(p, data, material_id)
    dirs = find_system_filament_dirs() if system_dirs is None else [Path(d) for d in system_dirs]
    now = retrieved_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return _import_bambu(p, data, dirs, now)
