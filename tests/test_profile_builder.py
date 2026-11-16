"""Tests for ProfileBuilder / model output as a Bambu Studio user preset"""

from src.data.models import FilamentProfile, MaterialSettings
from src.generator.profile_builder import ProfileBuilder


def _build(**kw):
    return ProfileBuilder().build_profile(
        "Acme Test PLA", "pla", "Acme",
        manual_overrides={"nozzle_temperature": [230]}, **kw)


def test_template_metadata_does_not_leak_into_output():
    data = _build().to_bambu_json()
    assert data["name"] == "Acme Test PLA"
    assert data["from"] == "User"
    assert data["instantiation"] == "true"
    assert data["filament_id"] != "GFL99"
    assert data["inherits"] == "Generic PLA"


def test_explicit_filament_id_is_used():
    data = _build(filament_id="PACME01").to_bambu_json()
    assert data["filament_id"] == "PACME01"


def test_to_dict_emits_string_arrays_for_scalars():
    s = MaterialSettings(nozzle_temperature=230, filament_flow_ratio=0.92,
                         filament_shrink="99.5%", enable_pressure_advance="1")
    s.additional_settings["filament_vendor"] = "Acme"
    d = s.to_dict()
    assert d["nozzle_temperature"] == ["230"]
    assert d["filament_flow_ratio"] == ["0.92"]
    assert d["filament_shrink"] == ["99.5%"]
    assert d["filament_vendor"] == ["Acme"]


def test_all_builder_values_are_string_arrays():
    data = _build().to_bambu_json()
    scalar_keys = {"name", "from", "inherits", "version", "setting_id",
                   "filament_id", "instantiation"}
    for key, value in data.items():
        if key in scalar_keys:
            assert isinstance(value, str), key
        else:
            assert isinstance(value, list), key
            assert all(isinstance(v, str) for v in value), key


def test_validate_passes_for_builder_output_without_bed_temperature():
    ok, errors = _build().validate()
    assert ok, errors


def test_validate_still_requires_nozzle_temperature_and_name():
    p = FilamentProfile(name="", material_type="PLA")
    ok, errors = p.validate()
    assert not ok
    assert any("Nozzle" in e for e in errors)
    assert any("name" in e for e in errors)


def test_validate_requires_a_plate_temperature():
    p = FilamentProfile(name="X", material_type="PLA")
    p.settings.nozzle_temperature = 220
    ok, errors = p.validate()
    assert not ok
    assert any("plate" in e for e in errors)
