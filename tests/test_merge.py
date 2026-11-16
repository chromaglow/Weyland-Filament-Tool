"""Tests for the provenance model, merge engine and report (wft-3abc8e.6)."""
import json
from pathlib import Path

from src.data.merge import (
    DEFAULT_PRECEDENCE,
    MergeConfig,
    merge,
    partition_of,
)
from src.data.report import write_report
from src.data.sourced import CollectedSettings, SourceKind, SourcedValue
from src.generator.material_file import build_filament_overrides, load_material

COLLECTED = Path(__file__).resolve().parents[1] / "docs/research/timemass-plant-vitamin/timemass_p1s_profiles.json"
K = SourceKind


def sv(key, value, kind=K.MAKER_GUIDE, status="published", source_id=None,
       retrieved_at="2026-11-16T10:00:00Z", raw=None, note=None):
    return SourcedValue(
        key=key, value=value, source_id=source_id or kind.value, source_kind=kind,
        source_url=f"https://example.test/{kind.value}", status=status,
        retrieved_at=retrieved_at, raw=raw if raw is not None else str(value), note=note,
    )


def collected(*values):
    c = CollectedSettings(material_id="m1", name="Test Material")
    for v in values:
        c.add(v)
    return c


def test_ac1_guide_beats_product_page_and_loser_kept(tmp_path):
    c = collected(sv("filament_flow_ratio", 0.92, K.MAKER_PRODUCT_PAGE), sv("filament_flow_ratio", 0.95, K.MAKER_GUIDE))
    r = merge(c)
    mv = r.filament["filament_flow_ratio"]
    assert mv.value == 0.95
    assert mv.winner.source_kind == K.MAKER_GUIDE
    assert [l.value for l in mv.losers] == [0.92]
    out = write_report(r, c, tmp_path / "r.md", generated_at="2026-11-16T12:00:00Z")
    text = out.read_text(encoding="utf-8")
    assert "0.92 (maker_product_page, maker_product_page)" in text


def test_ac2_precedence_configurable():
    c = collected(sv("filament_flow_ratio", 0.92, K.MAKER_PRODUCT_PAGE), sv("filament_flow_ratio", 0.95, K.MAKER_GUIDE))
    first = (K.MAKER_PRODUCT_PAGE, K.MAKER_GUIDE)
    prec = first + tuple(k for k in DEFAULT_PRECEDENCE if k not in first)
    assert merge(c, MergeConfig(precedence=prec)).filament["filament_flow_ratio"].value == 0.92


def test_ac3_imported_wins_and_status_imported():
    c = collected(
        sv("filament_flow_ratio", 0.9, K.IMPORTED_PROFILE, status="imported"),
        sv("filament_flow_ratio", 0.95, K.MAKER_GUIDE),
    )
    mv = merge(c).filament["filament_flow_ratio"]
    assert mv.value == 0.9 and mv.status == "imported"


def test_ac4_range_reduced_mid_with_range_keys(tmp_path):
    c = collected(sv("nozzle_temperature", (200, 220), raw="200-220 C"))
    r = merge(c)
    mv = r.filament["nozzle_temperature"]
    assert mv.value == 210 and mv.status == "derived" and mv.reduced_from == (200, 220)
    assert r.filament["nozzle_temperature_range_low"].value == 200
    assert r.filament["nozzle_temperature_range_high"].value == 220
    assert r.filament["nozzle_temperature_range_low"].status == "derived"
    text = write_report(r, c, tmp_path / "r.md").read_text(encoding="utf-8")
    ranges = text.split("## Ranges reduced")[1].split("## ")[0]
    assert "nozzle_temperature" in ranges and "200" in ranges and "220" in ranges


def test_range_policy_speed_low_and_override():
    c = collected(sv("outer_wall_speed", (40, 60)), sv("filament_max_volumetric_speed", (10, 14)))
    r = merge(c)
    assert r.process["outer_wall_speed"].value == 40
    assert r.filament["filament_max_volumetric_speed"].value == 10
    r2 = merge(c, MergeConfig(range_policy={"outer_wall_speed": "high"}))
    assert r2.process["outer_wall_speed"].value == 60


def test_ac5_defaults_are_assumptions_and_absent_otherwise(tmp_path):
    c = collected(sv("filament_flow_ratio", 0.95))
    r = merge(c, MergeConfig(defaults={"fan_min_speed": 35}))
    mv = r.filament["fan_min_speed"]
    assert mv.value == 35 and mv.status == "assumption" and mv.winner.source_kind == K.TOOL_DEFAULT
    assert mv in r.assumptions
    text = write_report(r, c, tmp_path / "r.md").read_text(encoding="utf-8")
    assert "fan_min_speed = 35" in text.split("## Assumptions")[1]
    for d in (r.filament, r.process, r.unpartitioned):
        assert "fan_max_speed" not in d


def test_ac6_partition_and_overrides():
    c = collected(
        sv("layer_height", 0.3), sv("outer_wall_speed", 60), sv("nozzle_temperature", 210),
        sv("totally_made_up_key", 1),
    )
    r = merge(c)
    assert r.filament_overrides() == {"nozzle_temperature": ["210"]}
    assert r.process_overrides() == {"layer_height": 0.3, "outer_wall_speed": 60}
    assert "totally_made_up_key" in r.unpartitioned
    assert partition_of("layer_height") == "process"
    assert partition_of("nozzle_temperature") == "filament"
    assert partition_of("nope") is None


def test_ac7_unnamed_bed_fans_out_to_plates():
    c = collected(sv("bed_temperature", 90))
    r = merge(c)
    for k in ("eng_plate_temp", "hot_plate_temp", "textured_plate_temp",
              "eng_plate_temp_initial_layer", "hot_plate_temp_initial_layer",
              "textured_plate_temp_initial_layer"):
        assert r.filament[k].value == 90 and r.filament[k].status == "derived", k
    assert "cool_plate_temp" not in r.filament
    assert "cool_plate_temp_initial_layer" not in r.filament
    for d in (r.filament, r.process, r.unpartitioned):
        assert "bed_temperature" not in d


def test_named_plate_beats_derived_at_same_rank():
    c = collected(sv("bed_temperature", 90), sv("textured_plate_temp", 80))
    assert merge(c).filament["textured_plate_temp"].value == 80


def test_single_value_beats_range_from_same_source():
    c = collected(sv("nozzle_temperature", (200, 220), source_id="s"), sv("nozzle_temperature", 215, source_id="s"))
    mv = merge(c).filament["nozzle_temperature"]
    assert mv.value == 215 and mv.reduced_from is None


def test_same_kind_tie_later_retrieval_wins():
    c = collected(
        sv("filament_flow_ratio", 0.9, source_id="a", retrieved_at="2026-11-01T00:00:00Z"),
        sv("filament_flow_ratio", 0.93, source_id="b", retrieved_at="2026-11-10T00:00:00Z"),
    )
    assert merge(c).filament["filament_flow_ratio"].value == 0.93


def test_ac8_existing_collected_file_loads():
    cs = CollectedSettings.from_collected_file(COLLECTED, "timemass-fire-gen2")
    nozzle = cs.for_key("nozzle_temperature")
    kinds = {(v.source_kind, v.status) for v in nozzle}
    assert (K.MAKER_PRODUCT_PAGE, "published") in kinds
    assert (K.MAKER_GUIDE, "published") in kinds
    assert cs.for_key("cool_plate_temp") == []  # not_published -> no candidate
    assert all(v.raw and v.retrieved_at and v.source_url for v in cs.values)
    r = merge(cs)
    assert r.filament["textured_plate_temp"].value == 90  # guide beats product page (75)
    assert r.filament["nozzle_temperature"].winner.source_kind == K.MAKER_GUIDE
    entry = load_material(COLLECTED, "timemass-fire-gen2")
    assert build_filament_overrides(entry)["nozzle_temperature"] == [230]


def test_json_round_trip_and_material_file_loadable(tmp_path):
    c = collected(
        sv("nozzle_temperature", (200, 220), raw="200-220 C", note="n"),
        sv("nozzle_temperature", 215, K.IMPORTED_PROFILE, status="imported"),
        sv("layer_height", 0.3),
    )
    p = tmp_path / "c.json"
    p.write_text(json.dumps(c.to_json()), encoding="utf-8")
    assert load_material(p, "m1")["name"] == "Test Material"
    back = CollectedSettings.from_collected_file(p, "m1")
    order = lambda v: (v.key, v.source_kind.value)
    assert sorted(back.values, key=order) == sorted(c.values, key=order)


def test_report_is_deterministic_and_lists_not_emitted(tmp_path):
    c = collected(sv("zzz_unknown", 1), sv("layer_height", 0.3), sv("nozzle_temperature", 210))
    r = merge(c)
    a = write_report(r, c, tmp_path / "a.md", generated_at="T").read_text(encoding="utf-8")
    b = write_report(r, c, tmp_path / "b.md", generated_at="T").read_text(encoding="utf-8")
    assert a == b
    assert a.startswith("# Research merge report: Test Material")
    assert "## Process settings" in a and "## Filament settings" in a
    assert "zzz_unknown" in a.split("## Not emitted")[1]
    assert a.count("| layer_height |") == 1
