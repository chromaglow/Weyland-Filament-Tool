"""Tests for exporting merged settings to presets plus report (wft-3abc8e.10)."""
import json

import pytest

from src.data.merge import MergeConfig, merge
from src.data.sourced import CollectedSettings, SourceKind, SourcedValue
from src.generator.bambu_keys import check_keys
from src.generator.merged_export import KeyCheckError, export_merged

K = SourceKind


def sv(key, value, kind=K.MAKER_GUIDE, status="published"):
    return SourcedValue(
        key=key, value=value, source_id=kind.value, source_kind=kind,
        source_url="https://example.test/p", status=status,
        retrieved_at="2026-11-16T10:00:00Z", raw=str(value),
    )


def collected(*values, material_id="m1"):
    c = CollectedSettings(material_id=material_id, name="Test Material")
    for v in values:
        c.add(v)
    return c


def run(c, tmp_path, **kw):
    return export_merged(c, tmp_path, name="Test Material PLA", manufacturer="Acme", **kw)


def load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def test_partition_and_four_files_written(tmp_path):
    c = collected(
        sv("filament_flow_ratio", 0.95),
        sv("nozzle_temperature", (210, 230)),
        sv("layer_height", 0.3),
        sv("outer_wall_speed", 120),
    )
    res = run(c, tmp_path)
    fil, proc = load(res.filament_path), load(res.process_path)
    assert fil["filament_flow_ratio"] == ["0.95"]
    assert fil["nozzle_temperature"] == ["220"]
    assert "layer_height" not in fil and "outer_wall_speed" not in fil
    assert proc["layer_height"] == "0.3"
    assert proc["outer_wall_speed"] == ["120", "120"]
    assert "filament_flow_ratio" not in proc
    assert load(res.collected_path)["materials"][0]["id"] == "m1"
    assert res.report_path.exists()
    assert {p.parent for p in (res.filament_path, res.process_path, res.collected_path, res.report_path)} == {tmp_path}
    assert check_keys(fil, "filament") == [] and check_keys(proc, "process") == []


def test_no_process_values_means_no_process_file(tmp_path):
    res = run(collected(sv("filament_flow_ratio", 0.95)), tmp_path)
    assert res.process_path is None
    assert not list(tmp_path.glob("*process*"))


def test_bed_temperature_becomes_per_plate_keys(tmp_path):
    res = run(collected(sv("bed_temperature", 60)), tmp_path)
    fil = load(res.filament_path)
    assert "bed_temperature" not in fil
    for plate in ("eng_plate", "hot_plate", "textured_plate"):
        assert fil[f"{plate}_temp"] == ["60"]
        assert fil[f"{plate}_temp_initial_layer"] == ["60"]


def test_unknown_key_raises_and_writes_nothing(tmp_path, monkeypatch):
    import src.generator.merged_export as me
    real = me.check_keys
    monkeypatch.setattr(me, "check_keys", lambda p, k: real({**p, "bogus_key": "1"}, k))
    with pytest.raises(KeyCheckError) as e:
        run(collected(sv("filament_flow_ratio", 0.95)), tmp_path)
    assert "bogus_key" in str(e.value)
    assert not list(tmp_path.iterdir())


def test_process_key_in_filament_preset_raises(tmp_path, monkeypatch):
    import src.generator.merged_export as me
    real = me.build_filament_preset
    monkeypatch.setattr(me, "build_filament_preset", lambda *a, **k: {**real(*a, **k), "layer_height": "0.2"})
    with pytest.raises(KeyCheckError, match="layer_height"):
        run(collected(sv("filament_flow_ratio", 0.95)), tmp_path)


def test_assumptions_and_unpartitioned_reported_not_written(tmp_path):
    c = collected(sv("filament_flow_ratio", 0.95), sv("made_up_key", 5))
    res = run(c, tmp_path, config=MergeConfig(defaults={"fan_min_speed": 100}))
    fil = load(res.filament_path)
    assert "made_up_key" not in json.dumps(fil)
    assert fil["fan_min_speed"] == ["100"]
    text = res.report_path.read_text(encoding="utf-8")
    assert "## Assumptions" in text and "fan_min_speed = 100" in text
    assert "made_up_key" in text.split("## Not emitted")[1]


def test_report_keeps_provenance_and_alternatives(tmp_path):
    c = collected(sv("filament_flow_ratio", 0.92, K.MAKER_PRODUCT_PAGE), sv("filament_flow_ratio", 0.95))
    text = run(c, tmp_path).report_path.read_text(encoding="utf-8")
    assert "https://example.test/p" in text and "0.92 (maker_product_page" in text


def test_template_defaults_listed_as_assumptions_with_value_and_template(tmp_path):
    res = run(collected(sv("filament_flow_ratio", 0.95)), tmp_path)
    fil = load(res.filament_path)
    keys = {d.key for d in res.template_defaults}
    assert {"eng_plate_temp", "enable_pressure_advance", "filament_deretraction_speed"} <= keys
    assert "filament_flow_ratio" not in keys  # sourced value keeps its status
    assert not keys & {"name", "inherits", "from", "version", "filament_id", "setting_id",
                       "filament_settings_id", "instantiation"}
    section = res.report_path.read_text(encoding="utf-8").split("## Assumptions")[1].split("## Not emitted")[0]
    assert "eng_plate_temp = 45" in section and "generic_pla" in section
    assert fil["eng_plate_temp"] == ["45"]  # preset contents unchanged


def test_derived_values_are_not_template_defaults(tmp_path):
    res = run(collected(sv("bed_temperature", 70)), tmp_path)
    keys = {d.key for d in res.template_defaults}
    assert "eng_plate_temp" not in keys and "hot_plate_temp" not in keys
