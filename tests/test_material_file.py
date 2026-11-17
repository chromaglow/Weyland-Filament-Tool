"""Tests for loading a material from the collected P1S settings file"""

import json
from pathlib import Path

import pytest

from src.generator.material_file import load_material, build_filament_overrides
from src.generator.profile_builder import ProfileBuilder

DATA = Path(__file__).resolve().parents[1] / "docs/research/timemass-plant-vitamin/timemass_p1s_profiles.json"
PV = "timemass-plant-vitamin-gen2"


@pytest.fixture(scope="module")
def entry():
    return load_material(DATA, PV)


def test_load_selects_by_id_and_rejects_unknown():
    assert load_material(DATA, PV)["id"] == PV
    with pytest.raises(KeyError):
        load_material(DATA, "no-such-material")


def test_loads_other_materials_by_id_too():
    ids = [m["id"] for m in json.loads(DATA.read_text(encoding="utf-8"))["materials"]]
    other = next(i for i in ids if i != PV)
    assert load_material(DATA, other)["id"] == other


def test_overrides_map_values_to_bambu_keys(entry):
    o = build_filament_overrides(entry)
    assert o["nozzle_temperature"] == [230]
    assert o["nozzle_temperature_initial_layer"] == [230]
    assert o["nozzle_temperature_range_low"] == [220]
    assert o["nozzle_temperature_range_high"] == [235]
    assert o["textured_plate_temp"] == [90]
    assert o["textured_plate_temp_initial_layer"] == [90]
    assert o["filament_flow_ratio"] == [0.95]
    assert o["pressure_advance"] == [0.05]
    assert o["filament_retraction_length"] == [0.4]
    assert o["filament_retraction_speed"] == [15]
    assert o["close_fan_the_first_x_layers"] == [3]
    assert o["fan_min_speed"] == [0]
    assert o["fan_cooling_layer_time"] == [100]
    assert o["fan_max_speed"] == [15]
    assert o["slow_down_layer_time"] == [8]
    assert o["overhang_fan_speed"] == [15]
    assert o["slow_down_for_layer_cooling"] == [1]
    assert o["additional_cooling_fan_speed"] == [0]


def test_notes_carry_drying_spool_door_and_cryogrip(entry):
    n = build_filament_overrides(entry)["filament_notes"][0]
    for text in ("68C/155F", "2 h", "external spool", "door open", "0.8 mm", "CryoGrip", "75"):
        assert text in n


def test_unpublished_plates_not_overridden(entry):
    o = build_filament_overrides(entry)
    for k in ("cool_plate_temp", "eng_plate_temp", "hot_plate_temp"):
        assert k not in o
    assert "assumption" in o["filament_notes"][0].lower()


def test_built_profile_is_user_preset_and_valid(entry):
    b = ProfileBuilder()
    p = b.build_profile("TimePlast TimeMass Plant Vitamin", "pla", "TimePlast",
                        manual_overrides=build_filament_overrides(entry, max_volumetric_speed=12),
                        filament_id="PTMPV01")
    assert p.validate() == (True, [])
    d = p.to_bambu_json()
    assert d["from"] == "User" and d["instantiation"] == "true"
    assert d["filament_id"] == "PTMPV01"
    assert d["textured_plate_temp"] == ["90"]
    assert d["textured_plate_temp_initial_layer"] == ["90"]
    assert d["filament_max_volumetric_speed"] == ["12"]
    assert d["filament_flow_ratio"] == ["0.95"]
    for k, v in d.items():
        if k not in {"name", "from", "inherits", "version", "setting_id", "filament_id", "instantiation"}:
            assert isinstance(v, list) and all(isinstance(x, str) for x in v), k


FIRE = "timemass-fire-gen2"
DET = "timemass-detergent-gen6"


def _build(mid, name, fid):
    b = ProfileBuilder()
    p = b.build_profile(name, "pla", "TimePlast",
                        manual_overrides=build_filament_overrides(load_material(DATA, mid)),
                        filament_id=fid)
    assert p.validate() == (True, [])
    return p.to_bambu_json()


@pytest.mark.parametrize("mid,name,fid", [
    (FIRE, "TimePlast TimeMass Fire", "PTMFI01"),
    (DET, "TimePlast TimeMass Detergent", "PTMDE01"),
])
def test_fire_and_detergent_presets_validate_with_p1s_recommended_values(mid, name, fid):
    d = _build(mid, name, fid)
    assert d["name"] == name and d["filament_id"] == fid
    assert d["from"] == "User" and d["instantiation"] == "true"
    # p1s_recommended wins over the product-page values (flow 0.92, bed 75)
    assert d["filament_flow_ratio"] == ["0.95"]
    assert d["textured_plate_temp"] == ["90"]
    assert d["textured_plate_temp_initial_layer"] == ["90"]
    assert d["nozzle_temperature"] == ["230"]
    assert d["nozzle_temperature_range_high"] == ["235"]
    assert d["filament_max_volumetric_speed"] == ["12"]
    assert d["pressure_advance"] == ["0.05"]
    for k, v in d.items():
        if k not in {"name", "from", "inherits", "version", "setting_id", "filament_id", "instantiation"}:
            assert isinstance(v, list) and all(isinstance(x, str) for x in v), k


def test_filament_ids_are_distinct():
    ids = {"PTMPV01", "PTMFI01", "PTMDE01"}
    assert len(ids) == 3


def test_fire_notes_carry_safety_and_common_warnings():
    n = build_filament_overrides(load_material(DATA, FIRE))["filament_notes"][0]
    for text in ("68C/155F", "external spool", "door open", "0.8 mm", "ventilation", "unattended"):
        assert text in n


def test_detergent_notes_say_gen6_and_not_gen5():
    n = build_filament_overrides(load_material(DATA, DET))["filament_notes"][0]
    for text in ("68C/155F", "external spool", "door open", "0.8 mm", "Gen 6", "gen5_reference"):
        assert text in n
    assert "Gen 5" in n
