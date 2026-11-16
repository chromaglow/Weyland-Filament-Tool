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


def run(tmp_path, argv, transport=None, **kw):
    out = []
    code = main(argv + ["--cache-dir", str(tmp_path / "cache")], transport=transport or Fake(),
                say=out.append, now=NOW, min_interval=0, system_dirs=[], **kw)
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
    assert not (out / "Plant Vitamin process.json").exists()  # no source supplied process values
    report = (out / "plant-vitamin.report.md").read_text(encoding="utf-8")
    assert "timeplast-product-page" in report and "OrcaSlicer/OrcaSlicer" in report
    assert "Unmapped page items" in report
    assert str(out) in text
    assert "nozzle_temperature" in text and "timeplast-product-page" in text
    assert "49 page items" in text and "report" in text
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
    code, text = run(tmp_path, research_args(tmp_path, "--source", f"import={process_source(tmp_path)}"))
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
    code, text = run(tmp_path, research_args(tmp_path, "--source", f"import={process_source(tmp_path)}", "--install", "--bambu-dir", str(root)),
                     ask=lambda q: "n", running=lambda: False)
    assert code == 0, text
    for d in ("123456", "default"):
        assert (root / "user" / d / "filament" / "Plant Vitamin.json").exists()
        assert (root / "user" / d / "process" / "Plant Vitamin process.json").exists()


def test_install_refuses_while_bambu_runs(tmp_path):
    root = _bambu(tmp_path)
    code, text = run(tmp_path, research_args(tmp_path, "--source", f"import={process_source(tmp_path)}", "--install", "--bambu-dir", str(root)),
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
