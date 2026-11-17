"""Source A adapter tests: saved fixtures + fake transport only, no live network."""
import logging
from pathlib import Path

import pytest

from src.data.merge import merge
from src.data.sourced import SourceKind
from src.scrapers.http_client import PoliteFetcher, TransportResponse
from src.scrapers.source_manufacturer import (
    SOURCE_ID,
    collect_from_url,
    parse_product_page,
)

FIX = Path(__file__).parent / "fixtures" / "sources" / "source_a"
PV_URL = "https://www.timeplast.com/shop/p/timemass-plant-vitamin-filament"
FIRE_URL = "https://www.timeplast.com/shop/p/timemass-fire"
NOW = "2026-11-16T12:00:00Z"


def _html(name):
    return (FIX / name).read_text(encoding="utf-8")


def _vals(result):
    return {(v.key, v.value) for v in result.settings.values}


def _one(result, key, value=None):
    found = [v for v in result.settings.for_key(key) if value is None or v.value == value]
    assert len(found) == 1, (key, found)
    return found[0]


@pytest.fixture(scope="module")
def pv():
    return parse_product_page(_html("plant_vitamin.html"), PV_URL, NOW)


def test_plant_vitamin_expected_values(pv):
    vals = _vals(pv)
    expected = {
        ("nozzle_temperature", 230),
        ("nozzle_temperature_initial_layer", 230),
        ("nozzle_temperature", (220, 240)),
        ("close_fan_the_first_x_layers", 3),
        ("fan_min_speed", 0),
        ("fan_cooling_layer_time", 100),
        ("fan_max_speed", 15),
        ("slow_down_layer_time", 8),
        ("reduce_fan_stop_start_freq", False),
        ("slow_down_for_layer_cooling", True),
        ("overhang_fan_speed", 15),
        ("filament_max_volumetric_speed", 12),
        ("filament_retraction_length", 0.4),
        ("filament_retraction_speed", 15),
        ("pressure_advance", 0.05),
        ("filament_flow_ratio", 0.92),
    }
    assert expected <= vals
    assert not any(k == "bed_temperature" or "plate_temp" in k for k, _ in vals)


def test_provenance_on_every_value(pv):
    assert pv.settings.values
    for v in pv.settings.values:
        assert v.status == "published"
        assert v.source_id == SOURCE_ID
        assert v.source_kind == SourceKind.MAKER_PRODUCT_PAGE
        assert v.source_url == PV_URL
        assert v.retrieved_at == NOW
        assert v.raw


def test_raw_text_is_verbatim_and_range_is_tuple(pv):
    rng = _one(pv, "nozzle_temperature", (220, 240))
    assert isinstance(rng.value, tuple)
    assert "220" in rng.raw and "240" in rng.raw and "°" in rng.raw
    assert "92%" in _one(pv, "filament_flow_ratio").raw


def test_unmapped_phrases_listed_and_logged(caplog):
    with caplog.at_level(logging.WARNING):
        res = parse_product_page(_html("plant_vitamin.html"), PV_URL, NOW)
    joined = "\n".join(res.unmapped)
    for label in ("Force Cooling for Overhangs", "Pre-Start Fan Time", "Ramming Speed"):
        assert label in joined
        assert label in caplog.text
    assert "Nozzle Temperature" not in joined
    assert "Flow Ratio" not in joined


def test_name_from_page_title(pv):
    assert pv.name == "Plant Vitamin - Gen 2"


def test_fire_page_same_guide_values():
    res = parse_product_page(_html("fire.html"), FIRE_URL, NOW)
    assert res.name == "Fire - Gen 2"
    assert ("nozzle_temperature", (220, 240)) in _vals(res)
    assert ("filament_flow_ratio", 0.92) in _vals(res)
    assert all(v.source_url == FIRE_URL for v in res.settings.values)


def test_crlf_fixture_parses_same(pv):
    crlf = _html("plant_vitamin.html").replace("\n", "\r\n")
    res = parse_product_page(crlf, PV_URL, NOW)
    assert _vals(res) == _vals(pv)


def test_page_without_guide_yields_nothing_not_guesses():
    res = parse_product_page("<html><title>X - Timeplast</title><body>Nice filament</body></html>", PV_URL, NOW)
    assert res.settings.values == []
    assert res.unmapped == []


def test_merges_nozzle_single_beats_range(pv):
    m = merge(pv.settings)
    assert m.filament["nozzle_temperature"].value == 230
    assert m.filament["filament_flow_ratio"].value == 0.92


def _fetcher(tmp_path, pages):
    calls = []

    def transport(url, headers, timeout):
        calls.append(url)
        if url.endswith("/robots.txt"):
            return TransportResponse(200, b"User-agent: *\nAllow: /\n")
        return TransportResponse(200, pages[url].encode("utf-8"))

    f = PoliteFetcher(cache_dir=tmp_path / "cache", min_interval=0, transport=transport)
    return f, calls


def test_collect_from_url_uses_fetcher_and_cache(tmp_path):
    f, calls = _fetcher(tmp_path, {PV_URL: _html("plant_vitamin.html")})
    res = collect_from_url(PV_URL, f, retrieved_at=NOW)
    assert ("filament_max_volumetric_speed", 12) in _vals(res)
    assert res.settings.material_id
    collect_from_url(PV_URL, f, retrieved_at=NOW)
    assert calls.count(PV_URL) == 1  # second call served from cache


def test_collect_from_url_robots_disallow(tmp_path):
    from src.scrapers.http_client import RobotsDisallowedError

    def transport(url, headers, timeout):
        return TransportResponse(200, b"User-agent: *\nDisallow: /\n")

    f = PoliteFetcher(cache_dir=tmp_path / "c", min_interval=0, transport=transport)
    with pytest.raises(RobotsDisallowedError):
        collect_from_url(PV_URL, f, retrieved_at=NOW)
