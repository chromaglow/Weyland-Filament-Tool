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


# --- per-plate bed temperature mapping (wft-3abc8e.4) ---

from src.data.models import ScrapedData

PLATES = ("cool_plate", "eng_plate", "hot_plate", "textured_plate")


def _scraped(temps, conf=1.0):
    return ScrapedData(source="t", url="http://x", temperatures=temps, confidence=conf)


def _build_scraped(*scraped, **kw):
    b = ProfileBuilder()
    p = b.build_profile("Acme Test PLA", "pla", "Acme",
                        scraped_data=list(scraped), **kw)
    return b, p.to_bambu_json()


def test_bed_temperature_is_never_emitted():
    _, data = _build_scraped(_scraped({"nozzle": 215, "bed": 70}))
    assert "bed_temperature" not in data
    assert "bed_temperature" not in _build().to_bambu_json()


def test_bed_temperature_manual_override_is_not_emitted():
    p = ProfileBuilder().build_profile(
        "A", "pla", "Acme", manual_overrides={"bed_temperature": [60]})
    assert "bed_temperature" not in p.to_bambu_json()


def test_single_bed_value_fills_eng_hot_textured_keeps_cool_template():
    b, data = _build_scraped(_scraped({"bed": 70}))
    for plate in ("eng_plate", "hot_plate", "textured_plate"):
        assert data[f"{plate}_temp"] == ["70"]
        assert data[f"{plate}_temp_initial_layer"] == ["70"]
    # generic_pla template cool plate is 35 and stays
    assert data["cool_plate_temp"] == ["35"]
    assert set(b.last_derived_keys) == {
        f"{p}_temp{s}" for p in ("eng_plate", "hot_plate", "textured_plate")
        for s in ("", "_initial_layer")}


def test_explicit_per_plate_values_map_to_matching_keys():
    _, data = _build_scraped(_scraped({
        "cool_plate": 30, "eng_plate": 50, "hot_plate": 60, "textured_plate": 55}))
    assert data["cool_plate_temp"] == ["30"]
    assert data["eng_plate_temp"] == ["50"]
    assert data["hot_plate_temp"] == ["60"]
    assert data["textured_plate_temp"] == ["55"]
    # initial layer defaults to the plate value
    for plate, v in zip(PLATES, ("30", "50", "60", "55")):
        assert data[f"{plate}_temp_initial_layer"] == [v]


def test_explicit_initial_layer_values_and_precedence_over_single_bed():
    b, data = _build_scraped(_scraped({
        "bed": 70, "hot_plate": 65, "hot_plate_initial_layer": 68}))
    assert data["hot_plate_temp"] == ["65"]
    assert data["hot_plate_temp_initial_layer"] == ["68"]
    assert data["eng_plate_temp"] == ["70"]
    assert "hot_plate_temp" not in b.last_derived_keys
    assert "eng_plate_temp" in b.last_derived_keys


def test_manual_override_beats_scraped_bed():
    _, data = _build_scraped(
        _scraped({"bed": 70}), manual_overrides={"hot_plate_temp": [75]})
    assert data["hot_plate_temp"] == ["75"]


def test_plate_values_are_string_arrays():
    _, data = _build_scraped(_scraped({"bed": 70}))
    keys = [k for k in data if k.endswith(("_plate_temp", "_plate_temp_initial_layer"))]
    assert len(keys) >= 7
    for k in keys:
        assert isinstance(data[k], list) and all(isinstance(x, str) for x in data[k])
