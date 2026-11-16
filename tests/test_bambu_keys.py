"""Tests for the Bambu Studio key catalogue and check_keys"""

import json
from pathlib import Path

import pytest

from src.generator.bambu_keys import check_keys, load_catalogue

FIX = Path(__file__).parent / "fixtures" / "bambu_presets"


def load(name):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


def test_catalogue_records_version_and_loads_without_install():
    cat = load_catalogue()
    assert cat["bambu_studio_version"]
    assert "nozzle_temperature" in cat["filament"]
    assert "layer_height" in cat["process"]


@pytest.mark.parametrize("name", [
    "Generic PLA @BBL A1.json", "Bambu ABS @BBL A1.json", "Generic PETG @BBL A1.json",
    "TimePlast TimeMass Fire.json", "TimePlast TimeMass Detergent.json",
    "TimePlast TimeMass Plant Vitamin.json",
])
def test_filament_fixtures_pass(name):
    assert check_keys(load(name), "filament") == []


@pytest.mark.parametrize("name", [
    "0.20mm Standard @BBL P1P.json", "0.30mm TimeMass @BBL P1S 0.8 nozzle.json",
])
def test_process_fixtures_pass(name):
    assert check_keys(load(name), "process") == []


def test_bed_temperature_is_unknown():
    problems = check_keys({"bed_temperature": ["60"]}, "filament")
    assert len(problems) == 1 and "bed_temperature" in problems[0]
    assert "unknown" in problems[0]


def test_process_key_in_filament_is_flagged():
    problems = check_keys({"layer_height": "0.2"}, "filament")
    assert len(problems) == 1
    assert "layer_height" in problems[0] and "process-only" in problems[0]


def test_unknown_key_in_process():
    assert "unknown" in check_keys({"nonsense_key": 1}, "process")[0]


def test_bad_kind_raises():
    with pytest.raises(ValueError):
        check_keys({}, "printer")
