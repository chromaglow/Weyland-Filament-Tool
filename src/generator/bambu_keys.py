"""Catalogue of valid Bambu Studio preset keys, taken from real system presets.

The catalogue (bambu_keys.json beside this file) is the union of keys found in
every system filament and process preset of a Bambu Studio install, so it loads
without Bambu Studio present. The Bambu Studio profile-bundle version it was
taken from is recorded in the JSON.
"""

import json
from functools import lru_cache
from pathlib import Path

CATALOGUE_PATH = Path(__file__).with_name("bambu_keys.json")
KINDS = ("filament", "process")


@lru_cache(maxsize=1)
def load_catalogue() -> dict:
    return json.loads(CATALOGUE_PATH.read_text(encoding="utf-8"))


def check_keys(preset: dict, kind: str) -> list[str]:
    """Return problems for a preset: unknown keys, and process-only keys in a filament preset."""
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}, got {kind!r}")
    cat = load_catalogue()
    valid = set(cat[kind])
    other = set(cat["process" if kind == "filament" else "filament"])
    problems = []
    for key in preset:
        if key in valid:
            continue
        if kind == "filament" and key in other:
            problems.append(f"{key}: process-only key in a filament preset")
        else:
            problems.append(f"{key}: unknown {kind} key")
    return problems
