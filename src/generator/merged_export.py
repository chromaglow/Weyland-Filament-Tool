"""Export a merged CollectedSettings to Bambu presets plus provenance files.

Writes into a caller-chosen folder (never into the Bambu Studio folder):
filament preset, process preset (only when process values exist), the
collected-settings JSON with provenance, and the markdown report.

Both presets are checked with check_keys before anything is written; a bad
key raises KeyCheckError and leaves the folder untouched. Unpartitioned keys
appear only in the report.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from src.data.merge import MergeConfig, MergeResult, merge
from src.data.report import write_report
from src.data.sourced import CollectedSettings
from src.generator import process_builder as pb
from src.generator.bambu_keys import check_keys
from src.generator.process_parent import ProcessParent
from src.generator.profile_builder import ProfileBuilder


class KeyCheckError(ValueError):
    """A preset to be written holds keys Bambu Studio does not accept."""

    def __init__(self, problems: Dict[str, List[str]]):
        self.problems = problems
        lines = [f"{kind} preset: {p}" for kind, ps in problems.items() for p in ps]
        super().__init__("Refusing to write presets with invalid keys:\n" + "\n".join(lines))


@dataclass(frozen=True)
class TemplateDefault:
    """A preset value no source supplied; it comes from the tool's template."""
    key: str
    value: str
    template: str


# Keys that identify or file the preset rather than describe the filament.
_IDENTITY_KEYS = frozenset({
    "name", "from", "inherits", "version", "instantiation", "filament_id", "setting_id",
    "filament_settings_id", "filament_type", "filament_vendor", "compatible_printers",
    "compatible_printers_condition", "compatible_prints", "compatible_prints_condition",
})


def template_defaults(preset: Dict[str, Any], result: MergeResult, material_type: str) -> List[TemplateDefault]:
    """Preset keys that are neither sourced/derived values nor identity keys."""
    template = f"generic_{material_type.lower()}"
    out = []
    for key, value in preset.items():
        if key in result.filament or key in _IDENTITY_KEYS:
            continue
        text = ", ".join(_fmt(v) for v in value) if isinstance(value, list) else _fmt(value)
        out.append(TemplateDefault(key, text, template))
    return sorted(out, key=lambda d: d.key)


@dataclass
class ExportResult:
    filament_path: Path
    process_path: Optional[Path]
    collected_path: Path
    report_path: Path
    merge_result: MergeResult
    template_defaults: List[TemplateDefault] = field(default_factory=list)
    process_note: Optional[str] = None  # why no process preset was written, when none was


def build_filament_preset(result: MergeResult, name: str, material_type: str, manufacturer: str,
                          filament_id: Optional[str] = None,
                          setting_id: Optional[str] = None) -> Dict[str, Any]:
    builder = ProfileBuilder()
    profile = builder.build_profile(name, material_type, manufacturer,
                                    manual_overrides=result.filament_overrides(),
                                    filament_id=filament_id, setting_id=setting_id)
    ok, errors = profile.validate()
    if not ok:
        raise ValueError(f"Filament profile {name} invalid: {errors}")
    return profile.to_bambu_json()


def _fmt(value: Any) -> str:
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


# Process values Bambu writes with a percent sign; sources publish the bare number.
_PERCENT_KEYS = frozenset({"sparse_infill_density", "infill_wall_overlap"})


def process_entry(result: MergeResult, name: str, parent: ProcessParent) -> Dict[str, Any]:
    """Adapter: flat Bambu process keys -> a process preset under `parent`.

    Identity, parent and printer come from the chosen ProcessParent (never a
    built-in printer). Speed and acceleration keys become per-extruder-variant
    arrays like Bambu's own presets; all other values are plain strings.
    """
    n = len(parent.variants) if parent.variants else 1
    preset: Dict[str, Any] = {
        "name": name,
        "print_settings_id": name,
        "from": "User",
        "inherits": parent.inherits,
        "version": pb.VERSION,
        "compatible_printers": [parent.machine],
    }
    if parent.variants:
        preset["print_extruder_id"] = ["1"] * n
        preset["print_extruder_variant"] = list(parent.variants)
    for key, value in result.process_overrides().items():
        text = _fmt(value)
        if key in _PERCENT_KEYS and not text.endswith("%"):
            text += "%"
        per_variant = "speed" in key or "acceleration" in key
        preset[key] = [text] * n if per_variant else text
    return preset


def export_merged(collected: CollectedSettings, out_dir: Union[str, Path], *, name: str,
                  manufacturer: str, material_type: str = "pla", filament_id: Optional[str] = None,
                  setting_id: Optional[str] = None, process_name: Optional[str] = None,
                  process_parent: Optional[ProcessParent] = None, config: Optional[MergeConfig] = None,
                  generated_at: Optional[str] = None) -> ExportResult:
    config = config or MergeConfig()
    result = merge(collected, config)

    filament = build_filament_preset(result, name, material_type, manufacturer, filament_id, setting_id)
    process, process_note = None, None
    if not result.process:
        process_note = "No source gave process settings; no process preset written."
    elif process_parent is None:
        process_note = (f"{len(result.process)} process settings found but no printer and nozzle size were given, "
                        "so no process preset was written (give --printer and --nozzle).")
    else:
        process = process_entry(result, process_name or f"{name} process", process_parent)

    problems = {"filament": check_keys(filament, "filament")}
    if process is not None:
        problems["process"] = check_keys(process, "process")
    problems = {k: v for k, v in problems.items() if v}
    if problems:
        raise KeyCheckError(problems)

    defaults = template_defaults(filament, result, material_type)

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    def dump(path: Path, data: Dict[str, Any]) -> Path:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return path

    filament_path = dump(out / f"{name}.json", filament)
    process_path = dump(out / f"{process['name']}.json", process) if process is not None else None
    collected_path = dump(out / f"{collected.material_id}.collected.json", collected.to_json())
    report_path = write_report(result, collected, out / f"{collected.material_id}.report.md",
                               generated_at=generated_at, precedence=config.precedence,
                              template_defaults=defaults, process_note=process_note)
    return ExportResult(filament_path, process_path, collected_path, report_path, result, defaults, process_note)
