"""Choosing the parent process preset from printer + nozzle (offline fixtures only)."""
from pathlib import Path

import pytest

from src.generator.process_parent import ProcessParentError, find_process_parent

SYS = Path(__file__).parent / "fixtures" / "bambu_system"
MACHINES, PROCESSES = [SYS / "machine"], [SYS / "process"]


def find(printer, nozzle, **kw):
    return find_process_parent(printer, nozzle, machine_dirs=MACHINES, process_dirs=PROCESSES, **kw)


def test_p1s_08_takes_the_machine_presets_default_print_profile():
    p = find("Bambu Lab P1S", "0.8")
    assert p.machine == "Bambu Lab P1S 0.8 nozzle"
    assert p.inherits == "0.40mm Standard @BBL X1C 0.8 nozzle"
    assert p.variants == ["Direct Drive Standard", "Direct Drive High Flow"]


def test_other_printer_gets_its_own_parent_and_variants():
    p = find("Bambu Lab A1", "0.4")
    assert p.inherits == "0.20mm Standard @BBL A1"
    assert p.variants == ["Direct Drive Standard"]  # found further up the inherits chain


def test_short_printer_name_and_numeric_nozzle_are_accepted():
    assert find("P1S", 0.8).machine == "Bambu Lab P1S 0.8 nozzle"


def test_parent_override_replaces_default_print_profile():
    p = find("Bambu Lab P1S", "0.8", parent_override="0.20mm Standard @BBL A1")
    assert p.inherits == "0.20mm Standard @BBL A1" and p.machine == "Bambu Lab P1S 0.8 nozzle"


def test_unknown_printer_nozzle_combination_is_an_error_that_names_it():
    with pytest.raises(ProcessParentError, match="P1S 0.6 nozzle"):
        find("Bambu Lab P1S", "0.6")


def test_parent_missing_from_system_presets_is_an_error():
    with pytest.raises(ProcessParentError, match="No Such Preset"):
        find("Bambu Lab P1S", "0.8", parent_override="No Such Preset")
