# Research Merge Spec: provenance model and precedence

Consumed by wft-3abc8e.6 (model and merge), .7/.8 (adapters emit the model), .9 (import), .10 (export and report).
Design only; no code changes in this task.

## Purpose
One tool-internal model for collected filament and process settings, where every value carries its provenance, plus a deterministic merge that picks one winner per key, records the losers, and marks every unpublished value as an assumption.

## Existing code this builds on
| Item | Decision |
|------|----------|
| `src/generator/material_file.py` loads the collected JSON (`settings.<section>.<key> = {value, status, note}`) | Extend, do not break. `load_material()` and `build_filament_overrides()` keep working on the unchanged file. New fields are optional and additive. |
| Statuses in the file today: `official_product_page`, `official_general_guide`, `not_published`, `estimate` | Read through a fixed mapping (below). The file is never rewritten with new status names. |
| `MaterialSettings` / `FilamentProfile` (`src/data/models.py`) | Reused as the output target: merged filament-key winners are applied through `ProfileBuilder` `manual_overrides` (Bambu key names, array-of-string values via `_to_string_array`). `MaterialSettings.bed_temperature` is NOT used (see Bed temperature). |
| `ProfileComparator` (`src/data/comparison.py`) | Not reused. It merges `ScrapedData` on a fixed set of fields with confidence weighting and has no source-kind precedence, no provenance, no process keys. `merge()` is new; the comparator stays for the existing scrape path. |
| `process_builder.build_process_preset()` | Process-key winners feed this path. It currently reads the collected-file layout; .10 adds a thin adapter from `CollectedSettings` process keys to its `entry` shape (or an overrides dict). wft-a5fea2 added printer and nozzle as inputs: `--printer`/`--nozzle` pick the machine preset and its `default_print_profile` as parent (`src/generator/process_parent.py`), and the manufacturer page adapter now emits process keys. |

## Data model

### Source kinds (precedence rank)
| `source_kind` | Meaning | Default rank (1 = wins) |
|---------------|---------|-------------------------|
| `imported_profile` | A profile file the user imported (Bambu/Orca JSON) | 1 |
| `maker_guide` | Manufacturer general printing guide | 2 |
| `maker_product_page` | Manufacturer SKU/product page | 3 |
| `community_repo` | Community profile repo (e.g. GitHub Orca/Bambu JSON) | 4 |
| `third_party_guide` | Third-party guide or review | 5 |
| `tool_default` | Template/tool default, always status `assumption` | 6 |

This order is a LEAD DECISION (main session, wft-3abc8e.2 note) and replaces the order in the issue description (product page > guide > imported ...). Reason: it matches the rule applied to the user's own collected file (guide beat product page: flow 0.95 over 0.92, bed 90 over 75) and treats the user's own profile as their choice. The order is configurable per run (`MergeConfig.precedence`); the above is the default.

### Status
`published` (a source states the value for this key), `derived` (computed from published values: range reduction, single bed value fanned to plates, unit conversion), `assumption` (no source publishes it; tool default), `imported` (came from an imported user profile).

Mapping from the existing file: `official_product_page` -> `published` + `maker_product_page`; `official_general_guide` -> `published` + `maker_guide`; `estimate` -> `derived`; `not_published` -> no value (treated as absent, so the key falls to the next source or becomes an assumption). An entry may carry optional `source_id`, `source_url`, `retrieved_at`, `raw`, `source_kind` fields; when absent the loader fills `source_id` and `source_url` from the material's `source_url` and `retrieved_at` from the file's `generated`.

### Python signatures
```python
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Sequence, Tuple, Union

Status = Literal["published", "derived", "assumption", "imported"]
Partition = Literal["filament", "process"]

class SourceKind(str, Enum):
    IMPORTED_PROFILE = "imported_profile"
    MAKER_GUIDE = "maker_guide"
    MAKER_PRODUCT_PAGE = "maker_product_page"
    COMMUNITY_REPO = "community_repo"
    THIRD_PARTY_GUIDE = "third_party_guide"
    TOOL_DEFAULT = "tool_default"

DEFAULT_PRECEDENCE: Tuple[SourceKind, ...] = (
    SourceKind.IMPORTED_PROFILE, SourceKind.MAKER_GUIDE, SourceKind.MAKER_PRODUCT_PAGE,
    SourceKind.COMMUNITY_REPO, SourceKind.THIRD_PARTY_GUIDE, SourceKind.TOOL_DEFAULT,
)

@dataclass(frozen=True)
class SourcedValue:
    key: str                       # Bambu key name, e.g. "nozzle_temperature", "eng_plate_temp", "layer_height"
    value: Union[int, float, str, bool, Tuple[Union[int, float], Union[int, float]]]  # a 2-tuple is a published range
    source_id: str                 # stable id, e.g. "timeplast-product-page"
    source_kind: SourceKind
    source_url: Optional[str]      # URL, or file path for imported profiles
    status: Status
    retrieved_at: str              # ISO 8601 UTC
    raw: str                       # verbatim source text the value came from ("200-220 C")
    note: Optional[str] = None

@dataclass
class CollectedSettings:
    material_id: str
    name: str
    values: List[SourcedValue] = field(default_factory=list)   # all candidates, many per key allowed
    def add(self, sv: SourcedValue) -> None: ...
    def for_key(self, key: str) -> List[SourcedValue]: ...
    @classmethod
    def from_collected_file(cls, path: Union[str, Path], material_id: str) -> "CollectedSettings": ...  # via load_material()
    def to_json(self) -> Dict[str, Any]: ...   # superset of the collected-file layout; stays loadable by material_file.py

@dataclass(frozen=True)
class MergeConfig:
    precedence: Sequence[SourceKind] = DEFAULT_PRECEDENCE
    range_policy: Dict[str, Literal["low", "mid", "high", "first"]] = field(default_factory=dict)  # per key; defaults below
    defaults: Dict[str, Any] = field(default_factory=dict)      # tool defaults, used only as assumptions

@dataclass(frozen=True)
class MergedValue:
    key: str
    partition: Partition
    value: Any                       # single reduced value
    winner: SourcedValue
    losers: Tuple[SourcedValue, ...] # every other candidate, in precedence order
    reduced_from: Optional[Tuple[Any, Any]] = None  # the range, when a range was reduced
    status: Status = "published"     # winner status, or "derived" if reduced, "assumption" if default

@dataclass
class MergeResult:
    filament: Dict[str, MergedValue]
    process: Dict[str, MergedValue]
    unpartitioned: Dict[str, MergedValue]   # keys in neither catalogue; reported, not emitted
    assumptions: List[MergedValue]          # every MergedValue with status "assumption"
    def filament_overrides(self) -> Dict[str, List[str]]: ...  # Bambu array-of-string form for ProfileBuilder
    def process_overrides(self) -> Dict[str, Any]: ...         # input for the process_builder path

FILAMENT_KEYS: frozenset  # catalogue owned by wft-3abc8e.6 (nozzle_temperature*, *_plate_temp*, filament_*, fan_*, pressure_advance, ...)
PROCESS_KEYS: frozenset   # layer_height, wall_loops, *_speed, *_acceleration, sparse_infill_*, brim_*, skirt_*, ...

def partition_of(key: str) -> Optional[Partition]: ...
def merge(collected: CollectedSettings, config: Optional[MergeConfig] = None) -> MergeResult: ...
def write_report(result: MergeResult, collected: CollectedSettings, out_path: Union[str, Path]) -> Path: ...
```

## Merge rules
1. Group candidates by `key`. Ignore a candidate whose status is absent/not published.
2. Winner = candidate whose `source_kind` has the lowest index in `config.precedence`. Ties within one kind: later `retrieved_at` wins; if equal, first added. Kinds not listed in `precedence` rank last.
3. If no candidate exists and `config.defaults` has the key, emit a `tool_default` value with status `assumption`. If neither exists the key is omitted (never a silent default).
4. Range reduction (winner value is a 2-tuple): one value per key, endpoints preserved in `reduced_from` and in the report; status becomes `derived`. Defaults: temperature keys (`nozzle_temperature*`, `*_plate_temp*`) `mid` rounded to int; speed, `filament_max_volumetric_speed` and acceleration keys `low` (conservative); all others `first`. Overridable per key via `range_policy`. A published range for nozzle temperature also populates `nozzle_temperature_range_low`/`_high` as `derived` from the endpoints.
5. A source that states both a single recommended value and a range for the same key supplies two candidates; the single value wins within that source.
6. Partition: each winner is routed by `partition_of(key)`. A process key never enters `filament_overrides()` and a filament key never enters `process_overrides()`. Keys in neither catalogue go to `unpartitioned` and the report.

### Bed temperature
Bed temperature is per plate: `cool_plate_temp`, `eng_plate_temp`, `hot_plate_temp`, `textured_plate_temp` and the matching `<plate>_initial_layer` keys. The key `bed_temperature` is never emitted. A source that gives one unnamed bed temperature yields `derived` candidates for `eng_plate_temp`, `hot_plate_temp`, `textured_plate_temp` (and their `_initial_layer` keys), with the note "single bed value applied to eng/hot/textured"; `cool_plate_temp` is left to the template and reported as an assumption. A named-plate value always beats a derived one at the same precedence rank.

## Report format (`write_report`, markdown)
```
# Research merge report: <name>
Generated <ISO time>. Precedence: <order used>.
## Filament settings
| Key | Value | Status | Winner (source, URL, retrieved) | Raw | Losing alternatives |
## Process settings
(same columns)
## Ranges reduced
| Key | Published range | Policy | Value |
## Assumptions
- <key> = <value>: no source publishes it; tool default.
## Not emitted
- <unpartitioned keys and why>
```
Every `MergedValue` appears exactly once. Losing alternatives are listed as `value (source_id, kind)`, comma-separated. Output is deterministic (keys sorted) so it can be diffed.

## Non-goals
- No fetching, scraping, or file parsing (adapters .7/.8 and importer .9 produce `SourcedValue`).
- No writing of Bambu preset files or installation (exporter .10 and later tasks).
- No confidence scoring or numeric weighting; precedence is rank order only.
- No replacement of `ProfileComparator` or the existing scrape path.
- No change to the collected-file schema beyond optional additive fields; no GUI.
- No cross-material or cross-printer merging; one material and one printer per run.

## Acceptance Criteria
AC1: Given candidates for `filament_flow_ratio` from `maker_guide` (0.95) and `maker_product_page` (0.92), when `merge()` runs with the default config, then the merged value is 0.95, the winner is the guide, and the product-page value appears in `losers` and in the report's losing-alternatives column.
AC2: Given the same candidates and `MergeConfig(precedence=(MAKER_PRODUCT_PAGE, MAKER_GUIDE, ...))`, when `merge()` runs, then the winner is 0.92, proving precedence is configurable per run.
AC3: Given an `imported_profile` value and a `maker_guide` value for the same key, when `merge()` runs with the default config, then the imported value wins and its status is `imported`.
AC4: Given a candidate `nozzle_temperature` = (200, 220), when `merge()` runs, then the value is 210, status is `derived`, `reduced_from == (200, 220)`, `nozzle_temperature_range_low`/`_high` are 200/220, and the report lists the key under "Ranges reduced".
AC5: Given a key with no candidate but a value in `MergeConfig.defaults`, when `merge()` runs, then the result contains it with status `assumption` and `winner.source_kind == tool_default`, and it appears in `result.assumptions` and the report's Assumptions section; given no candidate and no default, then the key is absent from every result dict.
AC6: Given winners for `layer_height` and `outer_wall_speed` (process) and `nozzle_temperature` (filament), when `filament_overrides()` and `process_overrides()` are called, then the filament dict holds only `nozzle_temperature` as a string array (`["210"]`), the process dict holds only the two process keys, and a key in neither catalogue lands in `unpartitioned` and is not emitted.
AC7: Given one unnamed bed temperature of 90 from a single source, when `merge()` runs, then `eng_plate_temp`, `hot_plate_temp`, `textured_plate_temp` and their `_initial_layer` keys are 90 with status `derived`, `cool_plate_temp` is not set by the source, and no result dict contains `bed_temperature`.
AC8: Given the existing collected file `docs/research/timemass-plant-vitamin/timemass_p1s_profiles.json`, when `CollectedSettings.from_collected_file()` loads a material, then `official_product_page` maps to `published`/`maker_product_page`, `official_general_guide` to `published`/`maker_guide`, `not_published` entries yield no candidate, and `load_material()` and `build_filament_overrides()` return the same results as before (the 37 existing tests stay green).

## Decisions
| Decision | Rationale |
|----------|-----------|
| Precedence order per the LEAD DECISION, configurable per run | Matches the user's own collected-file rule; user profile is their choice. The description's order is superseded. |
| `source_kind` separate from `status` | Status says how the value was obtained; kind says who published it and drives precedence. |
| New `merge()`, not `ProfileComparator` | Comparator is confidence-weighted over fixed fields and has no process keys or provenance. |
| Ranges: mid for temperatures, low for speeds | Mid matches common practice for temperature windows; low is the safe side for flow-limited speeds. Both overridable. |
| Unnamed bed value fans out as `derived` | Reproduces the manual TimeMass run while keeping it visible and never writing `bed_temperature`. |
| Extend the collected-file JSON additively | Keeps `material_file.py` and its tests working. |
