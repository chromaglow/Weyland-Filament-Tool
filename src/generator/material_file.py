"""
Load a material from the collected P1S settings file and map its
p1s_recommended values to Bambu Studio filament keys.

Reconciliation rule from the file: where the product page and the general
guide conflict, the guide wins (already reflected in p1s_recommended).
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional, Union


def load_material(path: Union[str, Path], material_id: str) -> Dict[str, Any]:
    """Return the entry of the file's "materials" array with the given id."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    materials = data.get("materials", [])
    if isinstance(materials, dict):
        materials = list(materials.values())
    for m in materials:
        if m.get("id") == material_id:
            return m
    raise KeyError(f"material id not found: {material_id}")


def _value(entry: Dict[str, Any], *keys: str) -> Any:
    node = entry["settings"]
    for k in keys:
        node = node[k]
    return node["value"]


def build_filament_overrides(
    entry: Dict[str, Any], max_volumetric_speed: Optional[float] = None
) -> Dict[str, Any]:
    """Map a material entry to ProfileBuilder manual_overrides (Bambu key names)."""
    rec = entry["p1s_recommended"]
    low = _value(entry, "temperature", "nozzle_range_product_c")[0]
    cooling = entry["settings"]["cooling"]
    cryo = _value(entry, "temperature", "bed_cryogrip_blue_c")
    drying = _value(entry, "drying", "guide")
    mvs = rec["max_volumetric_speed_mm3s"] if max_volumetric_speed is None else max_volumetric_speed

    notes = (
        f"{entry['name']}. Dry {drying['temp_c']}C/{drying['temp_f']}F at least "
        f"{drying['min_hours']} h {drying['when']}. Use the external spool, not AMS. "
        f"Print with the printer door open. Official nozzle is {rec['nozzle_mm']} mm. "
        f"Vendor CryoGrip plate bed temperature is {cryo}C (not mapped to a Bambu plate key). "
        f"Assumption: cool, engineering and smooth high-temp plate temperatures are not "
        f"published by the vendor and keep the Generic PLA template defaults."
    )
    safety = entry.get("use", {}).get("safety")
    if safety:
        notes += " Safety: " + "; ".join(safety) + "."
    if "gen5_reference" in entry:
        notes += (" Use Gen 6 values only; do not use the gen5_reference values "
                  "(Gen 5 differs in temperature, flow and bed).")

    return {
        "nozzle_temperature": [rec["nozzle_temp_c"]],
        "nozzle_temperature_initial_layer": [rec["nozzle_temp_c"]],
        "nozzle_temperature_range_low": [low],
        "nozzle_temperature_range_high": [rec["nozzle_temp_max_c"]],
        "textured_plate_temp": [rec["bed_textured_pei_c"]],
        "textured_plate_temp_initial_layer": [rec["bed_textured_pei_c"]],
        "filament_flow_ratio": [rec["flow_ratio"]],
        "filament_max_volumetric_speed": [mvs],
        "enable_pressure_advance": ["1"],
        "pressure_advance": [rec["pressure_advance"]],
        "filament_retraction_length": [rec["retraction"]["length_mm"]],
        "filament_retraction_speed": [rec["retraction"]["speed_mm_s"]],
        "filament_deretraction_speed": [rec["retraction"]["speed_mm_s"]],
        "close_fan_the_first_x_layers": [rec["cooling"]["off_first_layers"]],
        "fan_min_speed": [cooling["fan_min_pct"]["value"]],
        "fan_cooling_layer_time": [cooling["fan_min_layer_time_s"]["value"]],
        "fan_max_speed": [rec["cooling"]["max_pct"]],
        "slow_down_layer_time": [cooling["fan_max_layer_time_s"]["value"]],
        "overhang_fan_speed": [cooling["overhang_fan_pct"]["value"]],
        "slow_down_for_layer_cooling": [1 if cooling["slow_down_for_cooling"]["value"] else 0],
        "additional_cooling_fan_speed": [rec["aux_fan_pct"]],
        "filament_diameter": [_value(entry, "filament", "diameter_mm")],
        "filament_vendor": ["TimePlast"],
        "filament_notes": [notes],
    }
