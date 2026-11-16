"""
Build the TimeMass process (print settings) preset for a Bambu Lab P1S with a
0.8 mm nozzle from the collected settings file.

Every key name and value format below was checked against real Bambu Studio
presets (system process presets under APPDATA/BambuStudio/system/BBL/process
and the user's own process presets). Values with no confirmed key or format
are left out and listed in HAND_SET.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

PRESET_NAME = "0.30mm TimeMass @BBL P1S 0.8 nozzle"
# The P1S 0.8 mm machine preset's default_print_profile (no P1S-named 0.8 process preset exists).
BASE_PRESET = "0.40mm Standard @BBL X1C 0.8 nozzle"
PRINTER = "Bambu Lab P1S 0.8 nozzle"
VERSION = "2.6.0.3"
# The base preset carries one value per extruder variant; mirror that.
VARIANTS = ["Direct Drive Standard", "Direct Drive High Flow"]

# (setting, file value, why it was not applied)
HAND_SET: List[Tuple[str, str, str]] = [
    ("Brim type", "brim 6 mm / gap 0.15", "Width and gap are applied; the brim type value for the file's brim is not confirmed, so it stays on the slicer default (set Brim type by hand)."),
    ("Seam position", "aligned_or_back", "No single confirmed Bambu value for 'aligned or back'."),
    ("Smart scarf seam / scarf seam steps", "on, 155 deg, 10 steps", "Angle 155 is applied (it is also the base default); the seam-slope type value and the steps key are not confirmed."),
    ("Max travel detour", "10mm or 5%", "Only a plain number was seen in real presets; this format is not confirmed."),
    ("Smooth speed transition", "on", "No confirmed Bambu key (smooth coefficient 80 is applied)."),
    ("Top/bottom shell thickness", "1.2 mm", "Conflicts with 3 shell layers x 0.3 mm = 0.9 mm; the layer count (3) is applied, thickness is left on the base value."),
    ("Prime tower: flush into support", "on", "No confirmed Bambu key."),
    ("First layer infill speed", "not in file", "Base value (55) is above the 15 mm/s first layer speed; consider lowering it by hand."),
]


def _v(entry: Dict[str, Any], section: str, key: str) -> Any:
    return entry["settings"][section][key]["value"]


def _num(x: Union[int, float]) -> str:
    return str(int(x)) if float(x) == int(x) else str(x)


def _arr(x: Union[int, float]) -> List[str]:
    return [_num(x)] * len(VARIANTS)


def _first(x: Any) -> Any:
    """Where the file gives a range ([100, 120]) take the first value (p1s_recommended agrees)."""
    return x[0] if isinstance(x, list) else x


def build_process_preset(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Map one material entry's process sections to Bambu process-preset keys."""
    rec = entry["p1s_recommended"]
    width = _num(_v(entry, "geometry", "line_width_mm"))
    speeds = entry["settings"]["speed_mm_s"]
    accel = entry["settings"]["accel_mm_s2"]

    preset: Dict[str, Any] = {
        "name": PRESET_NAME,
        "print_settings_id": PRESET_NAME,
        "from": "User",
        "inherits": BASE_PRESET,
        "version": VERSION,
        "compatible_printers": [PRINTER],
        "print_extruder_id": ["1"] * len(VARIANTS),
        "print_extruder_variant": list(VARIANTS),
        "layer_height": _num(_v(entry, "geometry", "layer_height_mm")),
        "initial_layer_print_height": _num(_v(entry, "geometry", "initial_layer_height_mm")),
        "wall_loops": _num(_v(entry, "quality", "wall_loops")),
        "top_shell_layers": _num(_v(entry, "quality", "top_bottom_shell_layers")),
        "bottom_shell_layers": _num(_v(entry, "quality", "top_bottom_shell_layers")),
        "top_surface_pattern": _v(entry, "quality", "top_bottom_pattern"),
        "bottom_surface_pattern": _v(entry, "quality", "top_bottom_pattern"),
        "wall_infill_order": "inner wall/outer wall/infill",
        "sparse_infill_pattern": _v(entry, "infill", "pattern"),
        "sparse_infill_density": f"{_num(_first(rec['infill']['density_pct']))}%",
        "infill_wall_overlap": f"{_num(_v(entry, 'infill', 'wall_infill_overlap_pct'))}%",
        "infill_combination": "1" if _v(entry, "infill", "infill_combination") else "0",
        "detect_floating_vertical_shell": "1" if _v(entry, "infill", "detect_floating_shells") else "0",
        "enable_arc_fitting": "1" if _v(entry, "quality", "arc_fitting") else "0",
        "elefant_foot_compensation": _num(_v(entry, "quality", "elephant_foot_mm")),
        "detect_thin_wall": "1" if _v(entry, "quality", "detect_thin_walls") else "0",
        "slice_closing_radius": _num(_v(entry, "quality", "gap_closing_radius_mm")),
        "reduce_crossing_wall": "1" if _v(entry, "quality", "avoid_crossing_walls") else "0",
        "smooth_coefficient": _num(_v(entry, "quality", "smooth_coefficient")),
        "scarf_angle_threshold": _num(_v(entry, "quality", "scarf_seam_angle_deg")),
        "skirt_loops": _num(_v(entry, "adhesion", "skirt_loops")),
        "brim_width": _num(_v(entry, "adhesion", "brim_width_mm")),
        "brim_object_gap": _num(_v(entry, "adhesion", "brim_gap_mm")),
        "initial_layer_speed": _arr(speeds["initial_layer"]["value"]),
        "outer_wall_speed": _arr(speeds["outer_wall"]["value"]),
        "inner_wall_speed": _arr(speeds["inner_wall"]["value"]),
        "small_perimeter_speed": _arr(speeds["small_perimeter"]["value"]),
        "top_surface_speed": _arr(speeds["top_surface"]["value"]),
        "sparse_infill_speed": _arr(rec["speeds_mm_s"]["infill"]),
        "travel_speed": _arr(speeds["travel"]["value"]),
        "default_acceleration": _arr(accel["normal"]["value"]),
        "travel_acceleration": _arr(accel["travel"]["value"]),
        "initial_layer_acceleration": _arr(accel["initial_layer"]["value"]),
        "outer_wall_acceleration": _arr(accel["outer_wall"]["value"]),
        "inner_wall_acceleration": _arr(accel["inner_wall"]["value"]),
        "top_surface_acceleration": _arr(accel["top_surface"]["value"]),
        # Prime tower: always on at 40 mm / 4 mm brim. It only prints when 2+ filaments
        # are loaded, so it is harmless for the single-material Fire preset (which has
        # no prime tower spec) and matches Plant Vitamin / Detergent.
        "enable_prime_tower": "1",
        "prime_tower_width": "40",
        "prime_tower_brim_width": "4",
    }
    for key in ("line_width", "outer_wall_line_width", "inner_wall_line_width",
                "sparse_infill_line_width", "top_surface_line_width", "initial_layer_line_width",
                "initial_layer_infill_line_width", "internal_solid_infill_line_width",
                "support_line_width", "skin_infill_line_width", "skeleton_infill_line_width"):
        preset[key] = width
    return preset


def save_process_preset(preset: Dict[str, Any], out_dir: Union[str, Path]) -> Path:
    path = Path(out_dir) / f"{preset['name']}.json"
    path.write_text(json.dumps(preset, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
