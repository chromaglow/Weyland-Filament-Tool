"""Merge engine: one winner per key, losers kept, ranges reduced, gaps marked.

Precedence, range policy and bed-temperature rules follow
docs/design/research-merge-spec.md. Key partition comes from the Bambu key
catalogue (src/generator/bambu_keys.py); no second catalogue is kept here.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, Sequence, Tuple

from src.data.sourced import SourceKind, SourcedValue, Status
from src.generator.bambu_keys import load_catalogue

Partition = Literal["filament", "process"]

DEFAULT_PRECEDENCE: Tuple[SourceKind, ...] = (
    SourceKind.IMPORTED_PROFILE,
    SourceKind.MAKER_GUIDE,
    SourceKind.MAKER_PRODUCT_PAGE,
    SourceKind.COMMUNITY_REPO,
    SourceKind.THIRD_PARTY_GUIDE,
    SourceKind.TOOL_DEFAULT,
)

_cat = load_catalogue()
_shared = set(_cat["filament"]) & set(_cat["process"])  # metadata keys: not partitionable
FILAMENT_KEYS = frozenset(set(_cat["filament"]) - _shared)
PROCESS_KEYS = frozenset(set(_cat["process"]) - _shared)

PLATES = ("eng_plate_temp", "hot_plate_temp", "textured_plate_temp")
BED_FANOUT_NOTE = "single bed value applied to eng/hot/textured"


def partition_of(key: str) -> Optional[Partition]:
    if key in FILAMENT_KEYS:
        return "filament"
    if key in PROCESS_KEYS:
        return "process"
    return None


@dataclass(frozen=True)
class MergeConfig:
    precedence: Sequence[SourceKind] = DEFAULT_PRECEDENCE
    range_policy: Dict[str, Literal["low", "mid", "high", "first"]] = field(default_factory=dict)
    defaults: Dict[str, Any] = field(default_factory=dict)  # used only as assumptions


@dataclass(frozen=True)
class MergedValue:
    key: str
    partition: Optional[Partition]
    value: Any
    winner: SourcedValue
    losers: Tuple[SourcedValue, ...]
    reduced_from: Optional[Tuple[Any, Any]] = None
    status: Status = "published"
    policy: Optional[str] = None  # range policy applied, when a range was reduced


def _fmt(value: Any) -> str:
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


@dataclass
class MergeResult:
    filament: Dict[str, MergedValue]
    process: Dict[str, MergedValue]
    unpartitioned: Dict[str, MergedValue]
    assumptions: List[MergedValue]

    def all_values(self) -> List[MergedValue]:
        return [*self.filament.values(), *self.process.values(), *self.unpartitioned.values()]

    def filament_overrides(self) -> Dict[str, List[str]]:
        """Bambu array-of-string form, input for ProfileBuilder manual_overrides."""
        return {k: [_fmt(v.value)] for k, v in sorted(self.filament.items())}

    def process_overrides(self) -> Dict[str, Any]:
        return {k: v.value for k, v in sorted(self.process.items())}


def _default_policy(key: str) -> str:
    if key.startswith("nozzle_temperature") or "_plate_temp" in key:
        return "mid"
    if "speed" in key or "acceleration" in key:
        return "low"
    return "first"


def _reduce(rng: Tuple[Any, Any], policy: str) -> Any:
    lo, hi = rng
    if policy == "low":
        return lo
    if policy == "high":
        return hi
    if policy == "mid":
        return int(round((lo + hi) / 2))
    return lo  # "first"


def _expand_bed(sv: SourcedValue) -> List[Tuple[SourcedValue, bool]]:
    """Fan an unnamed bed value out to eng/hot/textured plate keys as derived."""
    suffix = "_initial_layer" if sv.key == "bed_temperature_initial_layer" else ""
    keys = [p + suffix for p in PLATES]
    if sv.key == "bed_temperature":
        keys += [p + "_initial_layer" for p in PLATES]
    return [(replace(sv, key=k, status="derived", note=BED_FANOUT_NOTE), True) for k in keys]


def merge(collected, config: Optional[MergeConfig] = None) -> MergeResult:
    config = config or MergeConfig()
    rank = {k: i for i, k in enumerate(config.precedence)}
    last = len(rank)

    # (sv, is_fanout, insertion order) grouped by key
    groups: Dict[str, List[Tuple[SourcedValue, bool, int]]] = {}
    order = 0
    for sv in collected.values:
        if sv.value is None:
            continue
        items = _expand_bed(sv) if sv.key in ("bed_temperature", "bed_temperature_initial_layer") else [(sv, False)]
        for item, fan in items:
            groups.setdefault(item.key, []).append((item, fan, order))
            order += 1

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for key, val in config.defaults.items():
        if key not in groups:
            groups[key] = [(SourcedValue(
                key=key, value=val, source_id="tool-default", source_kind=SourceKind.TOOL_DEFAULT,
                source_url=None, status="assumption", retrieved_at=now, raw=str(val),
                note="no source publishes it; tool default"), False, order)]
            order += 1

    merged: Dict[str, MergedValue] = {}
    for key, cands in groups.items():
        # lowest rank, then named-plate over fan-out, then later retrieval, then first added
        ranked = sorted(cands, key=lambda c: (rank.get(c[0].source_kind, last), c[1], _neg(c[0].retrieved_at), c[2]))
        win = ranked[0][0]
        if isinstance(win.value, tuple):  # a single value from the same source beats its range
            same = [c[0] for c in ranked if c[0].source_id == win.source_id and not isinstance(c[0].value, tuple)]
            if same:
                win = same[0]
        losers = tuple(c[0] for c in ranked if c[0] is not win)
        merged[key] = _build(key, win, losers, config)

    # a published nozzle range also fills the range keys, unless a source supplied them
    for key in [k for k, m in merged.items() if k == "nozzle_temperature" and m.reduced_from]:
        m = merged[key]
        for rk, endpoint in (("nozzle_temperature_range_low", m.reduced_from[0]),
                             ("nozzle_temperature_range_high", m.reduced_from[1])):
            if rk not in merged:
                w = replace(m.winner, key=rk, value=endpoint, status="derived",
                            note="from published nozzle temperature range")
                merged[rk] = MergedValue(rk, partition_of(rk), endpoint, w, (), None, "derived")

    result = MergeResult({}, {}, {}, [])
    for key in sorted(merged):
        m = merged[key]
        {"filament": result.filament, "process": result.process}.get(m.partition, result.unpartitioned)[key] = m
        if m.status == "assumption":
            result.assumptions.append(m)
    return result


def _neg(ts: str) -> Tuple[int, ...]:
    # later retrieved_at sorts first; ISO strings compare lexically, so invert code points
    return tuple(-ord(ch) for ch in ts)


def _build(key: str, win: SourcedValue, losers: Tuple[SourcedValue, ...], config: MergeConfig) -> MergedValue:
    part = partition_of(key)
    if isinstance(win.value, tuple):
        policy = config.range_policy.get(key, _default_policy(key))
        return MergedValue(key, part, _reduce(win.value, policy), win, losers, win.value, "derived", policy)
    return MergedValue(key, part, win.value, win, losers, None, win.status)
