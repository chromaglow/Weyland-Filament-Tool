"""Tests for the TimeMass process (print settings) preset builder"""

import json
from pathlib import Path

import pytest

from src.generator.material_file import load_material
from src.generator.process_builder import (
    BASE_PRESET, PRESET_NAME, HAND_SET, build_process_preset, save_process_preset,
)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs/research/timemass-plant-vitamin/timemass_p1s_profiles.json"
MATERIALS = ["timemass-plant-vitamin-gen2", "timemass-fire-gen2", "timemass-detergent-gen6"]


@pytest.fixture(scope="module")
def preset():
    return build_process_preset(load_material(DATA, MATERIALS[0]))


def test_identity_and_base(preset):
    assert preset["name"] == PRESET_NAME == "0.30mm TimeMass @BBL P1S 0.8 nozzle"
    assert preset["print_settings_id"] == PRESET_NAME
    assert preset["from"] == "User"
    assert preset["inherits"] == BASE_PRESET == "0.40mm Standard @BBL X1C 0.8 nozzle"
    assert preset["compatible_printers"] == ["Bambu Lab P1S 0.8 nozzle"]


def test_geometry_and_quality_values(preset):
    for k, v in {
        "layer_height": "0.3", "initial_layer_print_height": "0.35",
        "line_width": "0.8", "outer_wall_line_width": "0.8", "inner_wall_line_width": "0.8",
        "sparse_infill_line_width": "0.8", "top_surface_line_width": "0.8",
        "initial_layer_line_width": "0.8", "internal_solid_infill_line_width": "0.8",
        "wall_loops": "2", "top_shell_layers": "3", "bottom_shell_layers": "3",
        "top_surface_pattern": "monotonic", "bottom_surface_pattern": "monotonic",
        "wall_infill_order": "inner wall/outer wall/infill",
        "sparse_infill_pattern": "grid", "sparse_infill_density": "20%",
        "infill_wall_overlap": "10%", "infill_combination": "1",
        "enable_arc_fitting": "1", "elefant_foot_compensation": "0.1",
        "detect_thin_wall": "1", "slice_closing_radius": "0.1",
        "detect_floating_vertical_shell": "1", "reduce_crossing_wall": "1",
        "smooth_coefficient": "80", "scarf_angle_threshold": "155",
        "skirt_loops": "2", "brim_width": "6", "brim_object_gap": "0.15",
    }.items():
        assert preset[k] == v, k


def test_speeds_and_accelerations_are_string_arrays(preset):
    for k, v in {
        "initial_layer_speed": "15", "outer_wall_speed": "60", "inner_wall_speed": "90",
        "small_perimeter_speed": "35", "top_surface_speed": "40",
        "sparse_infill_speed": "100", "travel_speed": "160",
        "default_acceleration": "2000", "travel_acceleration": "4000",
        "initial_layer_acceleration": "300", "outer_wall_acceleration": "1500",
        "inner_wall_acceleration": "2000", "top_surface_acceleration": "1500",
    }.items():
        # 2 entries to match the base's two print_extruder_variant entries
        assert preset[k] == [v, v], k
    assert preset["print_extruder_id"] == ["1", "1"]
    assert preset["print_extruder_variant"] == ["Direct Drive Standard", "Direct Drive High Flow"]


def test_prime_tower_choice(preset):
    # on, 40 mm wide, 4 mm brim: safe for all three (only used when 2+ filaments are loaded)
    assert preset["enable_prime_tower"] == "1"
    assert preset["prime_tower_width"] == "40"
    assert preset["prime_tower_brim_width"] == "4"


def test_unconfirmed_keys_left_out_and_listed(preset):
    for k in ("brim_type", "seam_position", "max_travel_detour_distance", "top_shell_thickness",
              "initial_layer_infill_speed", "seam_slope_type"):
        assert k not in preset
    listed = " ".join(h[0] for h in HAND_SET).lower()
    for word in ("brim type", "seam", "detour", "shell thickness", "scarf", "flush"):
        assert word in listed, word


def test_all_values_strings_or_string_arrays(preset):
    for k, v in preset.items():
        if isinstance(v, list):
            assert all(isinstance(x, str) for x in v), k
        else:
            assert isinstance(v, str), k


@pytest.mark.parametrize("mid", MATERIALS[1:])
def test_same_process_values_for_all_three_materials(preset, mid):
    assert build_process_preset(load_material(DATA, mid)) == preset


def test_save_writes_json_named_after_preset(preset, tmp_path):
    path = save_process_preset(preset, tmp_path)
    assert path.name == PRESET_NAME + ".json"
    assert json.loads(path.read_text(encoding="utf-8")) == preset
