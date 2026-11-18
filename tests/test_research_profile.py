"""End-to-end tests for the research / import command. Offline: saved fixtures
and a fake transport only; --install goes to a tmp_path Bambu folder."""
import json
from pathlib import Path
from urllib.parse import unquote

from src.generator.bambu_keys import check_keys
from src.research_profile import main
from src.scrapers.http_client import TransportResponse

FIX = Path(__file__).parent / "fixtures"
PAGE_URL = "https://timeplast.example/products/plant-vitamin"
B_DIR = "resources/profiles/BBL/filament"
B_LEAF = "Bambu PLA Basic @BBL P1S 0.4 nozzle"
COMMUNITY = f"OrcaSlicer/OrcaSlicer:{B_DIR}/{B_LEAF}.json"
B_FILES = {
    B_LEAF: "bambu_pla_basic_bbl_p1s_0.4.json",
    "Bambu PLA Basic @base": "bambu_pla_basic_base.json",
    "fdm_filament_pla": "fdm_filament_pla.json",
    "fdm_filament_common": "fdm_filament_common.json",
}
NOW = "2026-11-16T12:00:00Z"


class Fake:
    def __init__(self):
        self.calls = []

    def __call__(self, url, headers, timeout):
        self.calls.append(url)
        if url.endswith("/robots.txt"):
            return TransportResponse(404, b"")
        if url == PAGE_URL:
            return TransportResponse(200, (FIX / "sources/source_a/plant_vitamin.html").read_bytes())
        name = unquote(url.rsplit("/", 1)[1])[: -len(".json")]
        return TransportResponse(200, (FIX / "sources/source_b" / B_FILES[name]).read_bytes())


SYS = FIX / "bambu_system"
PRINTER = ["--printer", "Bambu Lab P1S", "--nozzle", "0.8"]


def run(tmp_path, argv, transport=None, **kw):
    out = []
    code = main(argv + ["--cache-dir", str(tmp_path / "cache")], transport=transport or Fake(),
                say=out.append, now=NOW, min_interval=0, system_dirs=[],
                machine_dirs=[SYS / "machine"], process_dirs=[SYS / "process"], **kw)
    return code, "\n".join(out)


def research_args(tmp_path, *extra):
    return ["research", "--material", "Plant Vitamin", "--manufacturer", "TimePlast",
            "--source", f"manufacturer={PAGE_URL}", "--source", f"community={COMMUNITY}",
            "--out", str(tmp_path / "out"), *extra]


def test_research_two_sources_exports_checked_presets_and_report(tmp_path):
    code, text = run(tmp_path, research_args(tmp_path))
    assert code == 0, text
    out = tmp_path / "out"
    filament = json.loads((out / "Plant Vitamin.json").read_text(encoding="utf-8"))
    assert check_keys(filament, "filament") == []
    assert filament["nozzle_temperature"][0] == "230"  # product page beats community 220
    assert not (out / "Plant Vitamin process.json").exists()  # page has process values but no --printer/--nozzle was given
    report = (out / "plant-vitamin.report.md").read_text(encoding="utf-8")
    assert "timeplast-product-page" in report and "OrcaSlicer/OrcaSlicer" in report
    assert "Unmapped page items" in report
    assert str(out) in text
    assert "nozzle_temperature" in text and "timeplast-product-page" in text
    assert "11 page items" in text and "report" in text
    assert "Installed" not in text


def test_research_does_not_install_without_flag(tmp_path):
    bambu = tmp_path / "BambuStudio"
    (bambu / "user" / "default" / "filament").mkdir(parents=True)
    code, _ = run(tmp_path, research_args(tmp_path, "--bambu-dir", str(bambu)))
    assert code == 0
    assert list((bambu / "user" / "default" / "filament").iterdir()) == []


def test_research_needs_two_sources(tmp_path):
    code, text = run(tmp_path, ["research", "--material", "X", "--source", f"manufacturer={PAGE_URL}",
                                "--out", str(tmp_path / "out")])
    assert code != 0 and "two sources" in text
    assert not (tmp_path / "out").exists()


def test_research_with_imported_file_as_third_source(tmp_path):
    imp = FIX / "import" / "bambu_user.json"
    code, text = run(tmp_path, research_args(tmp_path, "--source", f"import={imp}"))
    assert code == 0, text
    report = (tmp_path / "out" / "plant-vitamin.report.md").read_text(encoding="utf-8")
    assert "imported" in report


def test_offline_uses_cache_then_misses_cleanly(tmp_path):
    code, _ = run(tmp_path, research_args(tmp_path))
    assert code == 0
    t = Fake()
    code, text = run(tmp_path, research_args(tmp_path, "--offline"), transport=t)
    assert code == 0, text
    assert t.calls == []
    out = []
    code = main(research_args(tmp_path, "--offline") + ["--cache-dir", str(tmp_path / "empty")],
                transport=Fake(), say=out.append, now=NOW, min_interval=0, system_dirs=[])
    assert code != 0 and len(out) == 1 and "offline" in out[0].lower()


def test_robots_disallow_is_one_line_error(tmp_path):
    class Deny(Fake):
        def __call__(self, url, headers, timeout):
            if url.endswith("/robots.txt"):
                return TransportResponse(200, b"User-agent: *\nDisallow: /\n")
            return super().__call__(url, headers, timeout)
    out = []
    code = main(research_args(tmp_path) + ["--cache-dir", str(tmp_path / "c")], transport=Deny(),
                say=out.append, now=NOW, min_interval=0, system_dirs=[])
    assert code != 0 and len(out) == 1 and "robots" in out[0].lower()
    assert not (tmp_path / "out").exists()


def test_import_round_trip_on_known_keys(tmp_path):
    src = FIX / "import" / "bambu_user.json"
    code, text = run(tmp_path, ["import", str(src), "--out", str(tmp_path / "out")])
    assert code == 0, text
    original = json.loads(src.read_text(encoding="utf-8"))
    exported = json.loads((tmp_path / "out" / f"{original['name']}.json").read_text(encoding="utf-8"))
    assert check_keys(exported, "filament") == []
    compared = 0
    for key in ("nozzle_temperature", "filament_flow_ratio"):
        if key in original:
            assert exported[key] == original[key], key
            compared += 1
    assert compared


def test_import_merged_with_online_source(tmp_path):
    src = FIX / "import" / "bambu_user.json"
    code, text = run(tmp_path, ["import", str(src), "--merge-with", f"manufacturer={PAGE_URL}",
                                "--out", str(tmp_path / "out")])
    assert code == 0, text
    assert list((tmp_path / "out").glob("*.report.md"))


def test_import_rejects_process_preset_with_one_line(tmp_path):
    out = []
    code = main(["import", str(FIX / "import" / "process_preset.json"), "--out", str(tmp_path / "o"),
                 "--cache-dir", str(tmp_path / "c")], say=out.append, now=NOW, system_dirs=[])
    assert code != 0 and len(out) == 1


def test_key_check_error_is_one_line(tmp_path, monkeypatch):
    from src import research_profile as rp
    from src.generator.merged_export import KeyCheckError

    def boom(*a, **k):
        raise KeyCheckError({"filament": ["unknown key zzz"]})
    monkeypatch.setattr(rp, "export_merged", boom)
    code, text = run(tmp_path, research_args(tmp_path))
    assert code != 0 and "zzz" in text and len(text.splitlines()) == 1


def process_source(tmp_path):
    """A collected-settings file that carries process values (the web adapters emit none)."""
    from src.data.sourced import CollectedSettings, SourceKind, SourcedValue
    cs = CollectedSettings("pv", "Plant Vitamin")
    cs.add(SourcedValue("layer_height", 0.3, "maker-notes", SourceKind.MAKER_GUIDE, None, "published", NOW, "0.3 mm"))
    path = tmp_path / "process-values.collected.json"
    path.write_text(json.dumps(cs.to_json()), encoding="utf-8")
    return path


def test_process_values_produce_process_preset(tmp_path):
    code, text = run(tmp_path, research_args(tmp_path, "--source", f"import={process_source(tmp_path)}", *PRINTER))
    assert code == 0, text
    process = json.loads((tmp_path / "out" / "Plant Vitamin process.json").read_text(encoding="utf-8"))
    assert process["layer_height"] == "0.3"


def _bambu(tmp_path):
    root = tmp_path / "BambuStudio"
    for d in ("123456", "default"):
        (root / "user" / d / "filament").mkdir(parents=True)
        (root / "user" / d / "process").mkdir(parents=True)
    return root


def test_install_writes_account_and_default_folders(tmp_path):
    root = _bambu(tmp_path)
    code, text = run(tmp_path, research_args(tmp_path, "--source", f"import={process_source(tmp_path)}", *PRINTER, "--install", "--bambu-dir", str(root)),
                     ask=lambda q: "n", running=lambda: False)
    assert code == 0, text
    for d in ("123456", "default"):
        assert (root / "user" / d / "filament" / "Plant Vitamin.json").exists()
        assert (root / "user" / d / "process" / "Plant Vitamin process.json").exists()


def test_install_refuses_while_bambu_runs(tmp_path):
    root = _bambu(tmp_path)
    code, text = run(tmp_path, research_args(tmp_path, "--source", f"import={process_source(tmp_path)}", *PRINTER, "--install", "--bambu-dir", str(root)),
                     ask=lambda q: "y", running=lambda: True)
    assert code != 0 and "running" in text
    assert not (root / "user" / "default" / "filament" / "Plant Vitamin.json").exists()


def test_rate_limit_on_robots_is_reported_as_rate_limit(tmp_path):
    from src.scrapers.source_community_profiles import RateLimitError

    class Limited(Fake):
        def __call__(self, url, headers, timeout):
            if url.endswith("/robots.txt"):
                raise RateLimitError("GitHub rate limit reached for " + url + "; resets later")
            return super().__call__(url, headers, timeout)
    out = []
    code = main(research_args(tmp_path) + ["--cache-dir", str(tmp_path / "c")], transport=Limited(),
                say=out.append, now=NOW, min_interval=0, system_dirs=[])
    assert code != 0 and len(out) == 1
    assert out[0].startswith("Error: rate limit reached") and "try again later" in out[0] and "robots.txt does not allow" not in out[0]
    assert not (tmp_path / "out").exists()


def _legacy_file(tmp_path, extra=None):
    data = {"type": "filament", "name": "Legacy", "from": "User",
            "bed_temperature": ["70"], "bed_temperature_initial_layer": ["75"],
            "nozzle_temperature": ["205"], "bogus_future_key": ["x"], "inherits": "Missing Parent"}
    data.update(extra or {})
    p = tmp_path / "legacy_in.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_import_legacy_bed_temperature_fans_out_as_derived(tmp_path):
    code, text = run(tmp_path, ["import", str(_legacy_file(tmp_path)), "--out", str(tmp_path / "out"),
                                "--name", "Legacy"])
    assert code == 0, text
    preset = json.loads((tmp_path / "out" / "Legacy.json").read_text(encoding="utf-8"))
    assert "bed_temperature" not in preset
    for plate in ("eng_plate_temp", "hot_plate_temp", "textured_plate_temp"):
        assert preset[plate][0] == "70" if isinstance(preset[plate], list) else preset[plate] == "70"
        init = preset[plate + "_initial_layer"]
        assert (init[0] if isinstance(init, list) else init) == "75"
    collected = json.loads((tmp_path / "out" / "legacy.collected.json").read_text(encoding="utf-8"))
    node = collected["materials"][0]["settings"]["collected"]["bed_temperature"]
    assert node["value"] == 70 and node["status"] == "imported"
    report = (tmp_path / "out" / "legacy.report.md").read_text(encoding="utf-8")
    row = next(l for l in report.splitlines() if l.startswith("| eng_plate_temp |"))
    assert "| 70 | derived |" in row


def test_import_surfaces_unknown_keys_and_warnings(tmp_path):
    code, text = run(tmp_path, ["import", str(_legacy_file(tmp_path)), "--out", str(tmp_path / "out"),
                                "--name", "Legacy"])
    assert code == 0, text
    preset = json.loads((tmp_path / "out" / "Legacy.json").read_text(encoding="utf-8"))
    assert "bogus_future_key" not in preset
    report = (tmp_path / "out" / "legacy.report.md").read_text(encoding="utf-8")
    assert "## Imported file notes" in report
    assert "bogus_future_key" in report
    assert "Missing Parent" in report
    assert "imported file notes" in text
    assert "bogus_future_key" in text and "Missing Parent" in text


def test_console_counts_template_defaults_and_prints_print_relevant_few(tmp_path):
    code, text = run(tmp_path, ["import", str(_legacy_file(tmp_path)), "--out", str(tmp_path / "out"),
                                "--name", "Legacy"])
    assert code == 0, text
    report = (tmp_path / "out" / "legacy.report.md").read_text(encoding="utf-8")
    section = report.split("## Assumptions")[1].split("## Not emitted")[0]
    n = int(text.split("Assumptions: ")[1].split()[0])
    assert n == section.count("\n- ") and n > 8
    assert "enable_pressure_advance = 1" in section and "template default from generic_" in section
    shown = [l for l in text.splitlines() if "(template default," in l]
    assert 0 < len(shown) <= 8
    assert any("temp" in l for l in shown)
    assert f"{n - len(shown)} more template defaults in the report" in text


def test_research_report_lists_template_defaults(tmp_path):
    code, text = run(tmp_path, research_args(tmp_path))
    assert code == 0, text
    report = (tmp_path / "out" / "plant-vitamin.report.md").read_text(encoding="utf-8")
    section = report.split("## Assumptions")[1].split("## Not emitted")[0]
    assert "enable_pressure_advance = 1" in section and "filament_deretraction_speed" in section
    n = int(text.split("Assumptions: ")[1].split()[0])
    assert n == section.count("\n- ")


SYSTEM_ID = __import__("re").compile(r"^G[A-Z]{1,3}S?\d{2}(_|$)")


def _research_ids(tmp_path, name, sub):
    args = ["research", "--material", "Plant Vitamin", "--manufacturer", "TimePlast",
            "--source", f"manufacturer={PAGE_URL}", "--source", f"community={COMMUNITY}",
            "--name", name, "--out", str(tmp_path / sub)]
    code, text = run(tmp_path, args)
    assert code == 0, text
    d = json.loads((tmp_path / sub / f"{name}.json").read_text(encoding="utf-8"))
    return d["filament_id"], d["setting_id"]


def test_research_ids_unique_per_name_stable_and_not_system_pattern(tmp_path):
    a1 = _research_ids(tmp_path, "Plant Vitamin", "a1")
    a2 = _research_ids(tmp_path, "Plant Vitamin", "a2")
    b = _research_ids(tmp_path, "Plant Fire", "b")
    assert a1 == a2
    assert a1[0] != b[0] and a1[1] != b[1]
    for value in (*a1, *b):
        assert not SYSTEM_ID.match(value), value
    assert a1[0] != a1[1]


def test_import_keeps_own_ids_unless_name_changes(tmp_path):
    src = FIX / "import" / "bambu_user.json"
    original = json.loads(src.read_text(encoding="utf-8"))
    code, text = run(tmp_path, ["import", str(src), "--out", str(tmp_path / "same")])
    assert code == 0, text
    same = json.loads((tmp_path / "same" / f"{original['name']}.json").read_text(encoding="utf-8"))
    if "filament_id" in original:
        assert same["filament_id"] == original["filament_id"]
    code, text = run(tmp_path, ["import", str(src), "--name", "Renamed Copy", "--out", str(tmp_path / "ren")])
    assert code == 0, text
    ren = json.loads((tmp_path / "ren" / "Renamed Copy.json").read_text(encoding="utf-8"))
    assert ren["filament_id"] != original.get("filament_id")
    assert not SYSTEM_ID.match(ren["filament_id"]) and not SYSTEM_ID.match(ren["setting_id"])


# --- process preset from the manufacturer page (wft-a5fea2) ---------------------------

def _process(tmp_path, *extra):
    code, text = run(tmp_path, research_args(tmp_path, *PRINTER, *extra))
    assert code == 0, text
    path = tmp_path / "out" / "Plant Vitamin process.json"
    return json.loads(path.read_text(encoding="utf-8")), text


def test_research_writes_process_preset_from_page_settings(tmp_path):
    proc, text = _process(tmp_path)
    assert check_keys(proc, "process") == []
    assert proc["inherits"] == "0.40mm Standard @BBL X1C 0.8 nozzle"
    assert proc["compatible_printers"] == ["Bambu Lab P1S 0.8 nozzle"]
    for k, v in {"layer_height": "0.3", "initial_layer_print_height": "0.35", "wall_loops": "2",
                 "sparse_infill_density": "20%", "sparse_infill_pattern": "grid",
                 "infill_wall_overlap": "10%", "brim_width": "6", "enable_prime_tower": "1",
                 "wall_infill_order": "inner wall/outer wall/infill", "line_width": "0.8"}.items():
        assert proc[k] == v, k
    assert proc["sparse_infill_speed"] == ["100", "100"]  # low end of 100-120
    assert proc["travel_acceleration"] == ["4000", "4000"]
    assert "Process preset:" in text and "inherits '0.40mm Standard @BBL X1C 0.8 nozzle'" in text


def test_process_values_trace_to_the_page_in_the_report(tmp_path):
    _process(tmp_path)
    report = (tmp_path / "out" / "plant-vitamin.report.md").read_text(encoding="utf-8")
    section = report.split("## Process settings")[1].split("## Ranges reduced")[0]
    row = next(l for l in section.splitlines() if l.startswith("| layer_height |"))
    assert "timeplast-product-page" in row and PAGE_URL in row and "Layer Height: 0.3 mm" in row and "published" in row
    row = next(l for l in section.splitlines() if l.startswith("| sparse_infill_speed |"))
    assert "| 100 | derived |" in row and "Infill: 100" in row and "120 mm/s" in row
    unmapped = report.split("## Unmapped page items")[1]
    assert "Seam Position" in unmapped and "Layer Height" not in unmapped


def test_process_preset_is_used_with_a_different_printer(tmp_path):
    code, text = run(tmp_path, research_args(tmp_path, "--printer", "Bambu Lab A1", "--nozzle", "0.4"))
    assert code == 0, text
    proc = json.loads((tmp_path / "out" / "Plant Vitamin process.json").read_text(encoding="utf-8"))
    assert proc["inherits"] == "0.20mm Standard @BBL A1"
    assert proc["compatible_printers"] == ["Bambu Lab A1 0.4 nozzle"]
    assert proc["outer_wall_speed"] == ["60"]


def test_parent_process_flag_overrides_default(tmp_path):
    proc, _ = _process(tmp_path, "--parent-process", "0.20mm Standard @BBL A1")
    assert proc["inherits"] == "0.20mm Standard @BBL A1"


def test_no_printer_means_no_process_preset_and_a_clear_message(tmp_path):
    code, text = run(tmp_path, research_args(tmp_path))
    assert code == 0, text
    assert not (tmp_path / "out" / "Plant Vitamin process.json").exists()
    assert "no printer and nozzle size were given" in text
    report = (tmp_path / "out" / "plant-vitamin.report.md").read_text(encoding="utf-8")
    assert "no process preset was written" in report


def test_unknown_printer_is_a_one_line_error_and_writes_nothing(tmp_path):
    code, text = run(tmp_path, research_args(tmp_path, "--printer", "Bambu Lab P1S", "--nozzle", "0.6"))
    assert code == 1 and text.startswith("Error:") and "P1S 0.6 nozzle" in text and chr(10) not in text
    assert not (tmp_path / "out").exists()


def test_nozzle_without_printer_is_a_usage_error(tmp_path):
    code, text = run(tmp_path, research_args(tmp_path, "--nozzle", "0.8"))
    assert code == 2 and "--printer" in text


def test_import_with_no_process_values_writes_no_process_preset_and_says_so(tmp_path):
    code, text = run(tmp_path, ["import", str(_legacy_file(tmp_path)), "--out", str(tmp_path / "out"),
                                "--name", "Legacy", *PRINTER])
    assert code == 0, text
    assert not list((tmp_path / "out").glob("*process*"))
    assert "no process preset" in text.lower()
    assert "No source gave process settings" in (tmp_path / "out" / "legacy.report.md").read_text(encoding="utf-8")


def test_install_puts_page_process_preset_next_to_filament_preset(tmp_path):
    root = _bambu(tmp_path)
    code, text = run(tmp_path, research_args(tmp_path, *PRINTER, "--install", "--bambu-dir", str(root)),
                     ask=lambda q: "n", running=lambda: False)
    assert code == 0, text
    for d in ("123456", "default"):
        assert (root / "user" / d / "filament" / "Plant Vitamin.json").exists()
        assert (root / "user" / d / "process" / "Plant Vitamin process.json").exists()
