"""Provenance model for collected filament/process settings.

Every value carries the source that published it, where it came from, how it
was obtained (status) and the raw text. See docs/design/research-merge-spec.md.
Reads the collected-settings JSON through src/generator/material_file.py
(read-only) and writes a superset of that layout.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

from src.generator.material_file import load_material

Status = Literal["published", "derived", "assumption", "imported"]
Scalar = Union[int, float, str, bool]
Value = Union[Scalar, Tuple[Union[int, float], Union[int, float]]]

SECTION = "collected"  # settings section written/read by to_json / from_collected_file


class SourceKind(str, Enum):
    IMPORTED_PROFILE = "imported_profile"
    MAKER_GUIDE = "maker_guide"
    MAKER_PRODUCT_PAGE = "maker_product_page"
    COMMUNITY_REPO = "community_repo"
    THIRD_PARTY_GUIDE = "third_party_guide"
    TOOL_DEFAULT = "tool_default"


@dataclass(frozen=True)
class SourcedValue:
    key: str
    value: Value  # a 2-tuple is a published range
    source_id: str
    source_kind: SourceKind
    source_url: Optional[str]
    status: Status
    retrieved_at: str
    raw: str
    note: Optional[str] = None

    def to_json(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "value": list(self.value) if isinstance(self.value, tuple) else self.value,
            "status": self.status,
            "source_id": self.source_id,
            "source_kind": self.source_kind.value,
            "source_url": self.source_url,
            "retrieved_at": self.retrieved_at,
            "raw": self.raw,
        }
        if self.note is not None:
            d["note"] = self.note
        return d

    @classmethod
    def from_json(cls, key: str, d: Dict[str, Any]) -> "SourcedValue":
        v = d["value"]
        return cls(
            key=key,
            value=tuple(v) if isinstance(v, list) else v,
            source_id=d["source_id"],
            source_kind=SourceKind(d["source_kind"]),
            source_url=d.get("source_url"),
            status=d["status"],
            retrieved_at=d["retrieved_at"],
            raw=d["raw"],
            note=d.get("note"),
        )


# Existing collected-file status -> (source kind, status). not_published -> no candidate.
_FILE_STATUS: Dict[str, Tuple[SourceKind, Status]] = {
    "official_product_page": (SourceKind.MAKER_PRODUCT_PAGE, "published"),
    "official_general_guide": (SourceKind.MAKER_GUIDE, "published"),
    "estimate": (SourceKind.TOOL_DEFAULT, "derived"),
}

# (section, key) in the existing collected file -> Bambu key name. Only entries
# with an unambiguous Bambu equivalent are mapped; the rest stay in the file.
_FILE_KEY_MAP: Dict[Tuple[str, str], str] = {
    ("temperature", "nozzle_c"): "nozzle_temperature",
    ("temperature", "nozzle_range_product_c"): "nozzle_temperature",
    ("temperature", "nozzle_range_guide_c"): "nozzle_temperature",
    ("temperature", "nozzle_initial_layer_c"): "nozzle_temperature_initial_layer",
    ("temperature", "bed_textured_pei_c_guide"): "textured_plate_temp",
    ("temperature", "bed_textured_pei_c_product"): "textured_plate_temp",
    ("temperature", "bed_cool_plate_c"): "cool_plate_temp",
    ("temperature", "bed_engineering_plate_c"): "eng_plate_temp",
    ("temperature", "bed_high_temp_plate_c"): "hot_plate_temp",
    ("cooling", "no_cooling_first_layers"): "close_fan_the_first_x_layers",
    ("cooling", "fan_min_pct"): "fan_min_speed",
    ("cooling", "fan_min_layer_time_s"): "fan_cooling_layer_time",
    ("cooling", "fan_max_pct"): "fan_max_speed",
    ("cooling", "fan_max_layer_time_s"): "slow_down_layer_time",
}


def _raw_text(value: Any) -> str:
    if isinstance(value, (list, tuple)) and len(value) == 2:
        return f"{value[0]}-{value[1]}"
    return str(value)


@dataclass
class CollectedSettings:
    material_id: str
    name: str
    values: List[SourcedValue] = field(default_factory=list)  # all candidates, many per key

    def add(self, sv: SourcedValue) -> None:
        self.values.append(sv)

    def for_key(self, key: str) -> List[SourcedValue]:
        return [v for v in self.values if v.key == key]

    @classmethod
    def from_collected_file(cls, path: Union[str, Path], material_id: str) -> "CollectedSettings":
        entry = load_material(path, material_id)
        with open(path, "r", encoding="utf-8") as f:
            generated = json.load(f).get("generated", "")
        cs = cls(material_id=entry["id"], name=entry.get("name", entry["id"]))
        url = entry.get("source_url")
        for section, items in entry.get("settings", {}).items():
            for fkey, item in items.items():
                if section == SECTION:
                    cs.add(SourcedValue.from_json(fkey, item))
                    for alt in item.get("alternatives", []):
                        cs.add(SourcedValue.from_json(fkey, alt))
                    continue
                bambu_key = _FILE_KEY_MAP.get((section, fkey))
                mapped = _FILE_STATUS.get(item.get("status", ""))
                if bambu_key is None or mapped is None or "value" not in item:
                    continue  # unmapped key, not_published, or no value
                kind, status = mapped
                value = item["value"]
                cs.add(SourcedValue(
                    key=bambu_key,
                    value=tuple(value) if isinstance(value, list) else value,
                    source_id=f"{entry['id']}-{kind.value}",
                    source_kind=kind,
                    source_url=url,
                    status=status,
                    retrieved_at=generated,
                    raw=_raw_text(value),
                    note=item.get("note"),
                ))
        return cs

    def to_json(self) -> Dict[str, Any]:
        """Superset of the collected-file layout; load_material() can read it."""
        section: Dict[str, Any] = {}
        for sv in self.values:
            node = section.get(sv.key)
            if node is None:
                section[sv.key] = sv.to_json()
            else:
                node.setdefault("alternatives", []).append(sv.to_json())
        return {
            "schema_version": "1.1",
            "materials": [{"id": self.material_id, "name": self.name, "settings": {SECTION: section}}],
        }
