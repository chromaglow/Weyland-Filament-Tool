"""Source B adapter tests: fixtures + fake transport only, no live network."""
import io
import json
from pathlib import Path
from urllib.parse import unquote

import pytest

from src.data.merge import merge
from src.data.sourced import SourceKind, SourcedValue
from src.scrapers.http_client import PoliteFetcher, RobotsDisallowedError, TransportResponse
from src.scrapers import source_community_profiles as scp
from src.scrapers.source_community_profiles import (
    InheritanceDepthError,
    ParentNotFoundError,
    RateLimitError,
    collect_profile,
    github_transport,
    raw_url,
)

FIX = Path(__file__).parent / "fixtures" / "sources" / "source_b"
REPO = "OrcaSlicer/OrcaSlicer"
DIR = "resources/profiles/BBL/filament"
LEAF = "Bambu PLA Basic @BBL P1S 0.4 nozzle"
BASE = "Bambu PLA Basic @base"
FILES = {
    LEAF: "bambu_pla_basic_bbl_p1s_0.4.json",
    BASE: "bambu_pla_basic_base.json",
    "fdm_filament_pla": "fdm_filament_pla.json",
    "fdm_filament_common": "fdm_filament_common.json",
}
NOW = "2026-11-16T12:00:00Z"


class FakeTransport:
    def __init__(self, extra=None, crlf=False, missing=()):
        self.calls = []
        self.extra = extra or {}
        self.crlf = crlf
        self.missing = set(missing)

    def __call__(self, url, headers, timeout):
        self.calls.append(url)
        if url.endswith("/robots.txt"):
            return TransportResponse(404, b"")
        name = unquote(url.rsplit("/", 1)[1])[: -len(".json")]
        if name in self.missing:
            return TransportResponse(404, b"")
        if name in self.extra:
            return TransportResponse(200, json.dumps(self.extra[name]).encode())
        text = (FIX / FILES[name]).read_text(encoding="utf-8")
        if self.crlf:
            text = text.replace("\r\n", "\n").replace("\n", "\r\n")
        return TransportResponse(200, text.encode())


def fetcher(tmp_path, transport):
    return PoliteFetcher(cache_dir=tmp_path / "cache", min_interval=0, transport=transport)


def leaf_url(name=LEAF):
    return raw_url(REPO, f"{DIR}/{name}.json")


def collect(tmp_path, transport=None, **kw):
    t = transport or FakeTransport()
    return collect_profile(fetcher(tmp_path, t), leaf_url(), retrieved_at=NOW, **kw), t


def one(profile, key):
    vals = profile.settings.for_key(key)
    assert len(vals) == 1, (key, vals)
    return vals[0]


def test_leaf_values_and_provenance(tmp_path):
    p, _ = collect(tmp_path)
    sv = one(p, "nozzle_temperature")
    assert sv.value == 220 and sv.status == "published"
    assert sv.source_kind is SourceKind.COMMUNITY_REPO
    assert sv.source_id == f"{REPO}:{DIR}/{LEAF}.json"
    assert sv.source_url == leaf_url()
    assert sv.retrieved_at == NOW and sv.raw == "220"
    # index 0 (standard variant) is used, not index 1
    assert one(p, "filament_flow_ratio").value == 0.98
    assert one(p, "filament_max_volumetric_speed").value == 21


def test_inherited_values_nearest_wins_and_point_at_supplying_file(tmp_path):
    p, _ = collect(tmp_path)
    fan = one(p, "fan_min_speed")  # pla 100 overrides common 35
    assert fan.value == 100 and fan.source_url == leaf_url("fdm_filament_pla")
    assert fan.source_id == f"{REPO}:{DIR}/{LEAF}.json"  # id stays the requested profile
    assert "inherited" in (fan.note or "")
    assert one(p, "cool_plate_temp").value == 35
    assert one(p, "fan_max_speed").source_url == leaf_url("fdm_filament_common")
    assert one(p, "filament_cost").value == 15.99  # base overrides pla
    assert p.chain == [LEAF, BASE, "fdm_filament_pla", "fdm_filament_common"]


def test_nil_means_no_value_and_falls_back_to_parent(tmp_path):
    p, _ = collect(tmp_path)
    for sv in p.settings.values:
        assert sv.value != "nil" and sv.raw != "nil"
    # leaf ["nil","0.4"] and common ["nil"]: nothing in the chain gives a value
    assert p.settings.for_key("filament_retraction_length") == []


def test_nil_in_child_falls_back_to_parent_value(tmp_path):
    t = FakeTransport(extra={LEAF: {"name": LEAF, "inherits": "fdm_filament_pla",
                                    "fan_min_speed": ["nil", "5"]}})
    p, _ = collect(tmp_path, t)
    sv = one(p, "fan_min_speed")
    assert sv.value == 100 and sv.source_url == leaf_url("fdm_filament_pla")


def test_nil_with_no_parent_value_emits_nothing(tmp_path):
    t = FakeTransport(extra={LEAF: {"name": LEAF, "filament_z_hop": ["nil", "0.6"]}})
    p, _ = collect(tmp_path, t)
    assert p.settings.for_key("filament_z_hop") == []


def test_crlf_fixture_files(tmp_path):
    p, _ = collect(tmp_path, FakeTransport(crlf=True))
    assert one(p, "nozzle_temperature").value == 220
    assert "\r" not in one(p, "filament_start_gcode").value


def test_unknown_keys_kept_as_extras_not_dropped(tmp_path):
    doc = json.loads((FIX / FILES[LEAF]).read_text(encoding="utf-8"))
    doc["x_community_note"] = ["hello", "x"]
    p, _ = collect(tmp_path, FakeTransport(extra={LEAF: doc}))
    assert p.extras["x_community_note"] == ["hello", "x"]
    assert p.settings.for_key("x_community_note") == []
    for k in ("type", "name", "inherits", "from", "instantiation", "setting_id"):
        assert k not in p.extras


def test_missing_parent_is_a_clear_error(tmp_path):
    with pytest.raises(ParentNotFoundError) as e:
        collect(tmp_path, FakeTransport(missing={"fdm_filament_pla"}))
    assert "fdm_filament_pla" in str(e.value) and BASE in str(e.value)


def test_depth_limit_and_cycle(tmp_path):
    with pytest.raises(InheritanceDepthError):
        collect(tmp_path, FakeTransport(extra={LEAF: {"name": LEAF, "inherits": LEAF}}))
    with pytest.raises(InheritanceDepthError):
        collect(tmp_path, FakeTransport(), max_depth=2)


def test_conflict_with_source_a_resolved_by_merge(tmp_path):
    p, _ = collect(tmp_path)
    p.settings.add(SourcedValue(
        key="nozzle_temperature", value=230, source_id="timeplast",
        source_kind=SourceKind.MAKER_PRODUCT_PAGE, source_url="https://example.invalid/p",
        status="published", retrieved_at=NOW, raw="230",
    ))
    m = merge(p.settings).filament["nozzle_temperature"]
    assert m.value == 230
    assert [v.value for v in m.losers] == [220]
    assert m.losers[0].source_kind is SourceKind.COMMUNITY_REPO


def test_robots_enforced_through_polite_fetcher(tmp_path):
    class Deny(FakeTransport):
        def __call__(self, url, headers, timeout):
            if url.endswith("/robots.txt"):
                return TransportResponse(200, b"User-agent: *\nDisallow: /\n")
            return super().__call__(url, headers, timeout)

    with pytest.raises(RobotsDisallowedError):
        collect(tmp_path, Deny())


def test_raw_url_and_repo_path_input(tmp_path):
    assert raw_url(REPO, "a b/c@d.json", ref="main") == (
        "https://raw.githubusercontent.com/OrcaSlicer/OrcaSlicer/main/a%20b/c%40d.json")
    p = collect_profile(fetcher(tmp_path, FakeTransport()), f"{REPO}:{DIR}/{LEAF}.json", retrieved_at=NOW)
    assert one(p, "nozzle_temperature").value == 220


# --- github transport: token handling and rate limit ---------------------

class FakeResp(io.BytesIO):
    def __init__(self, body, status=200, headers=None):
        super().__init__(body)
        self.status = status
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_token_from_env_sent_only_to_github_hosts(monkeypatch):
    seen = []

    def fake_open(req, timeout=None):
        seen.append(dict(req.header_items()))
        return FakeResp(b"{}")

    monkeypatch.setattr(scp, "open_no_redirect", fake_open)
    monkeypatch.setenv("WFT_GITHUB_TOKEN", "sekret")
    t = github_transport()
    t("https://raw.githubusercontent.com/x/y/main/a.json", {"User-Agent": "u"}, 5)
    t("https://example.com/a.json", {"User-Agent": "u"}, 5)
    assert seen[0].get("Authorization") == "Bearer sekret"
    assert "Authorization" not in seen[1]
    monkeypatch.delenv("WFT_GITHUB_TOKEN")
    t("https://raw.githubusercontent.com/x/y/main/a.json", {}, 5)
    assert "Authorization" not in seen[2]


def test_rate_limit_exhausted_raises_without_leaking_token(monkeypatch):
    def fake_open(req, timeout=None):
        return FakeResp(b"", 403, {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1800000000"})

    monkeypatch.setattr(scp, "open_no_redirect", fake_open)
    monkeypatch.setenv("WFT_GITHUB_TOKEN", "sekret")
    with pytest.raises(RateLimitError) as e:
        github_transport()("https://api.github.com/x", {}, 5)
    assert "1800000000" in str(e.value) and "sekret" not in str(e.value)


def test_token_never_forwarded_on_redirect_to_another_host(monkeypatch, tmp_path):
    from tests.stub_server import stub_server
    monkeypatch.setenv("WFT_GITHUB_TOKEN", "sekrit-token")
    monkeypatch.setattr(scp, "GITHUB_HOSTS", {"127.0.0.1"})  # stand-in for a GitHub host
    with stub_server({"/f": (200, {}, b"payload")}) as (b_url, b_seen):
        other = b_url.replace("127.0.0.1", "localhost")  # different host, same loopback
        with stub_server({"/robots.txt": (404, {}, b""),
                          "/r": (302, {"Location": other + "/f"}, b"")}) as (a_url, a_seen):
            fetcher = PoliteFetcher(cache_dir=tmp_path, min_interval=0,
                                    transport=scp.github_transport())
            resp = fetcher.get(a_url + "/r")
    assert resp.body == b"payload"
    assert a_seen[-1][1].get("authorization") == "Bearer sekrit-token"  # sent to the allowed host
    assert all("authorization" not in h for _, h in b_seen)  # never to the other host
    assert "sekrit-token" not in "".join(p.name + p.read_text(errors="ignore") for p in tmp_path.iterdir() if p.is_file())
