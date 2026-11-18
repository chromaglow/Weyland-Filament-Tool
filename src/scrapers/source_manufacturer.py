"""Source A adapter: manufacturer product page (Timeplast TimeMass guide).

Fetches a product URL through PoliteFetcher and parses the printing guide into
SourcedValue candidates (status "published", Bambu key names, ranges as
2-tuples). Matching is on label text, never on CSS class names. Numbered guide
items that are not mapped are logged and returned in `unmapped`, never guessed.

Field map: docs/research/online-sources.md ("Source A"). No bed temperatures
are published by this source, so none are emitted.

The guide also lists process (print) settings. A label is mapped to a Bambu
process key only where its meaning is unambiguous (the keys are the ones used by
src/generator/process_builder.py, checked against real presets); the rest stay in
`unmapped`. Speed and acceleration items share labels ("Travel", "Outer Wall"),
so they are told apart by unit (mm/s versus mm/s squared), not by position.
"""
from __future__ import annotations

import html
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from src.data.sourced import CollectedSettings, SourceKind, SourcedValue
from src.scrapers.http_client import PoliteFetcher

logger = logging.getLogger(__name__)

SOURCE_ID = "timeplast-product-page"

# item: "2.a Nozzle Temperature: 230C - description". Label has no colon.
_ITEM = re.compile(
    r"(?P<num>\d{1,2}\.[a-z])\s+(?P<label>[^:\d.][^:.]{2,60}?):\s*"
    r"(?P<body>.*?)(?=\s\d{1,2}\.[a-z]\s|\s\d{1,2}\.\s+[A-Z]|$)"
)
_DESC_SPLIT = re.compile(r"\s[—–-]\s")
_NUM = r"(\d+(?:\.\d+)?)"
_DASH = r"\s*[-–—]\s*"

Mapped = List[Tuple[str, object, Optional[str]]]


def _first_number(raw: str) -> Optional[float]:
    m = re.search(_NUM, raw)
    return _num(m.group(1)) if m else None


def _num(s: str):
    f = float(s)
    return int(f) if f.is_integer() else f


def _on_off(raw: str) -> Optional[bool]:
    m = re.match(r"\s*(ON|OFF)\b", raw, re.I)
    return None if not m else m.group(1).upper() == "ON"


def _single(key: str, cast: Callable = lambda x: x) -> Callable[[str], Mapped]:
    def f(raw: str) -> Mapped:
        n = _first_number(raw)
        return [] if n is None else [(key, cast(n), None)]
    return f


def _bool(key: str, note: Optional[str] = None) -> Callable[[str], Mapped]:
    def f(raw: str) -> Mapped:
        b = _on_off(raw)
        return [] if b is None else [(key, b, note)]
    return f


def _nozzle(raw: str) -> Mapped:
    n = _first_number(raw)
    if n is None:
        return []
    return [("nozzle_temperature", n, None), ("nozzle_temperature_initial_layer", n, None)]


def _nozzle_range(raw: str) -> Mapped:
    m = re.search(_NUM + r"\s*°?\s*C?" + _DASH + _NUM, raw)
    if not m:
        return []
    return [("nozzle_temperature", (_num(m.group(1)), _num(m.group(2))), None)]


def _fan_pair(fan_key: str, time_key: str, pattern: str) -> Callable[[str], Mapped]:
    def f(raw: str) -> Mapped:
        m = re.search(pattern, raw, re.I)
        return [] if not m else [(fan_key, _num(m.group(1)), None), (time_key, _num(m.group(2)), None)]
    return f


def _flow_ratio(raw: str) -> Mapped:
    n = _first_number(raw)
    if n is None:
        return []
    ratio = round(n / 100, 4) if "%" in raw else n
    return [("filament_flow_ratio", ratio, "page states percent; converted to ratio" if "%" in raw else None)]


def _percent_range(key: str) -> Callable[[str], Mapped]:
    def f(raw: str) -> Mapped:
        m = re.search(_NUM + r"\s*%?" + _DASH + _NUM + r"\s*%", raw)
        if m:
            return [(key, (_num(m.group(1)), _num(m.group(2))), None)]
        m = re.match(r"\s*" + _NUM + r"\s*%", raw)
        return [(key, _num(m.group(1)), None)] if m else []
    return f


def _range_or_single(key: str, unit: str) -> Callable[[str], Mapped]:
    """'100-120 mm/s' -> a range, '60 mm/s' -> a single value; the unit must match."""
    def f(raw: str) -> Mapped:
        m = re.match(r"\s*" + _NUM + r"(?:" + _DASH + _NUM + r")?\s*" + unit + r"\s*$", raw)
        if not m:
            return []
        return [(key, _num(m.group(1)) if m.group(2) is None else (_num(m.group(1)), _num(m.group(2))), None)]
    return f


def _count(*keys: str) -> Callable[[str], Mapped]:
    def f(raw: str) -> Mapped:
        m = re.match(r"\s*(\d+)\s*$", raw)
        return [] if not m else [(k, int(m.group(1)), None) for k in keys]
    return f


def _mm(*keys: str) -> Callable[[str], Mapped]:
    def f(raw: str) -> Mapped:
        m = re.match(r"\s*" + _NUM + r"\s*mm\s*$", raw)
        return [] if not m else [(k, _num(m.group(1)), None) for k in keys]
    return f


def _pattern(*keys: str, allowed: Tuple[str, ...]) -> Callable[[str], Mapped]:
    def f(raw: str) -> Mapped:
        word = raw.strip().lower()
        return [(k, word, None) for k in keys] if word in allowed else []
    return f


_SPEED_UNIT = r"mm/s(?!\s*[²2])"
_ACCEL_UNIT = r"mm/s\s*[²2]"
_LINE_WIDTH_KEYS = ("line_width", "outer_wall_line_width", "inner_wall_line_width",
                    "sparse_infill_line_width", "top_surface_line_width", "initial_layer_line_width",
                    "internal_solid_infill_line_width", "support_line_width", "initial_layer_infill_line_width",
                    "skin_infill_line_width", "skeleton_infill_line_width")
_TOP_BOTTOM_PATTERNS = ("monotonic", "concentric")
_SPARSE_PATTERNS = ("grid", "gyroid", "honeycomb", "cubic", "triangles", "line", "concentric")

_PROCESS_LABELS: Dict[str, Callable[[str], Mapped]] = {
    "gap closing radius": _mm("slice_closing_radius"),
    "arc fitting": _bool("enable_arc_fitting"),
    "elephant foot compensation": _mm("elefant_foot_compensation"),
    "wall loops": _count("wall_loops"),
    "detect thin walls": _bool("detect_thin_wall"),
    "top/bottom shell layers": _count("top_shell_layers", "bottom_shell_layers"),
    "top/bottom pattern": _pattern("top_surface_pattern", "bottom_surface_pattern", allowed=_TOP_BOTTOM_PATTERNS),
    "smooth coefficient": _count("smooth_coefficient"),
    "avoid crossing wall": _bool("reduce_crossing_wall"),
    "layer height": _mm("layer_height"),
    "initial layer height": _mm("initial_layer_print_height"),
    "line widths (all)": _mm(*_LINE_WIDTH_KEYS),
    "wall/infill overlap": _percent_range("infill_wall_overlap"),
    "infill combination": _bool("infill_combination"),
    "detect floating shells": _bool("detect_floating_vertical_shell"),
    "sparse infill density": _percent_range("sparse_infill_density"),
    "sparse pattern": _pattern("sparse_infill_pattern", allowed=_SPARSE_PATTERNS),
    "skirt loops": _count("skirt_loops"),
    "brim width": _mm("brim_width"),
    "brim gap": _mm("brim_object_gap"),
    "prime tower": _bool("enable_prime_tower"),
    "tower width": _mm("prime_tower_width"),
    "brim width (tower)": _mm("prime_tower_brim_width"),
}

# label -> key, for items told apart by unit
_SPEEDS = {"travel": "travel_speed", "initial layer": "initial_layer_speed", "outer wall": "outer_wall_speed",
           "inner wall": "inner_wall_speed", "small perimeter": "small_perimeter_speed",
           "top surface": "top_surface_speed", "infill": "sparse_infill_speed"}
_ACCELS = {"normal print": "default_acceleration", "travel": "travel_acceleration",
           "initial layer": "initial_layer_acceleration", "outer wall": "outer_wall_acceleration",
           "inner wall": "inner_wall_acceleration", "top surface": "top_surface_acceleration"}


def _unit_handler(label: str) -> Optional[Callable[[str], Mapped]]:
    def f(raw: str) -> Mapped:
        for table, unit in ((_ACCELS, _ACCEL_UNIT), (_SPEEDS, _SPEED_UNIT)):
            if label in table and re.search(_NUM + r"\s*" + unit, raw):
                return _range_or_single(table[label], unit)(raw)
        return []
    return f if label in _SPEEDS or label in _ACCELS else None


# Two items that only mean something together: Bambu has one 'wall_infill_order' key.
_WALL_ORDER = "wall order"
_INFILL_FIRST = "infill first"
_INNER_FIRST_VALUE = "inner wall/outer wall/infill"


# normalised label text -> handler
_LABELS: Dict[str, Callable[[str], Mapped]] = {
    "nozzle temperature": _nozzle,
    "nozzle temperature range": _nozzle_range,
    "no cooling for first layers": _single("close_fan_the_first_x_layers"),
    "fan minimum speed": _fan_pair("fan_min_speed", "fan_cooling_layer_time",
                                   r"(\d+(?:\.\d+)?)\s*%.*?(\d+(?:\.\d+)?)\s*seconds?"),
    "fan maximum speed": _fan_pair("fan_max_speed", "slow_down_layer_time",
                                   r"(\d+(?:\.\d+)?)\s*%.*?(\d+(?:\.\d+)?)\s*seconds?"),
    "keep fan always on": _bool("reduce_fan_stop_start_freq", "inferred mapping from 'Keep Fan Always On'"),
    "slow down for cooling": _bool("slow_down_for_layer_cooling"),
    "fan for overhangs": _single("overhang_fan_speed"),
    "max volumetric speed": _single("filament_max_volumetric_speed"),
    "retraction distance": _single("filament_retraction_length"),
    "retraction speed": _single("filament_retraction_speed"),
    "pressure advance": _single("pressure_advance"),
    "flow ratio": _flow_ratio,
    **_PROCESS_LABELS,
}


@dataclass
class ParseResult:
    settings: CollectedSettings
    name: str
    unmapped: List[str] = field(default_factory=list)


def _page_text(page: str) -> str:
    s = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", page)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def _title(page: str) -> str:
    m = re.search(r"(?is)<title[^>]*>(.*?)</title>", page)
    t = re.sub(r"\s+", " ", html.unescape(m.group(1))).strip() if m else ""
    return re.split(r"\s[—–-]\s*Timeplast$", t)[0].strip() or t


def _slug(url: str) -> str:
    last = urlparse(url).path.rstrip("/").rsplit("/", 1)[-1]
    return re.sub(r"[^a-z0-9]+", "-", last.lower()).strip("-") or "product"


def parse_product_page(page: str, url: str, retrieved_at: str,
                       material_id: Optional[str] = None) -> ParseResult:
    name = _title(page)
    settings = CollectedSettings(material_id=material_id or _slug(url), name=name)
    result = ParseResult(settings=settings, name=name)
    seen = set()
    deferred: Dict[str, Tuple[str, str]] = {}  # label -> (item number, value text)

    def add(mapped: Mapped, label: str, value_text: str) -> None:
        for key, value, note in mapped:
            settings.add(SourcedValue(
                key=key, value=value, source_id=SOURCE_ID,
                source_kind=SourceKind.MAKER_PRODUCT_PAGE, source_url=url,
                status="published", retrieved_at=retrieved_at,
                raw=f"{label}: {value_text}", note=note,
            ))

    def leave_unmapped(num: str, label: str, value_text: str) -> None:
        phrase = f"{num} {label}: {value_text}"
        result.unmapped.append(phrase)
        logger.warning("Source A: unmapped phrase %r (%s)", phrase, url)

    for m in _ITEM.finditer(_page_text(page)):
        label = m.group("label").strip()
        ident = (m.group("num"), label.lower())
        if ident in seen:  # page carries a desktop and a mobile copy
            continue
        seen.add(ident)
        value_text = _DESC_SPLIT.split(m.group("body").strip(), maxsplit=1)[0].strip()
        if label.lower() in (_WALL_ORDER, _INFILL_FIRST):
            deferred[label.lower()] = (m.group("num"), value_text)
            continue
        handler = _LABELS.get(label.lower()) or _unit_handler(label.lower())
        mapped = handler(value_text) if handler else []
        if not mapped:
            leave_unmapped(m.group("num"), label, value_text)
            continue
        add(mapped, label, value_text)

    _wall_infill_order(deferred, add, leave_unmapped)
    return result


def _wall_infill_order(deferred, add, leave_unmapped) -> None:
    """'Wall Order: Inner before Outer' with 'Infill First: OFF' is Bambu's
    'inner wall/outer wall/infill'. Any other combination, or one item alone,
    is not mapped."""
    order, infill = deferred.get(_WALL_ORDER), deferred.get(_INFILL_FIRST)
    if order and infill and re.fullmatch(r"inner\s+before\s+outer", order[1], re.I) and _on_off(infill[1]) is False:
        add([("wall_infill_order", _INNER_FIRST_VALUE, None)], "Wall Order",
            f"{order[1]}; Infill First: {infill[1]}")
        return
    for label, item in ((_WALL_ORDER, order), (_INFILL_FIRST, infill)):
        if item:
            leave_unmapped(item[0], label.title(), item[1])


def collect_from_url(url: str, fetcher: PoliteFetcher, retrieved_at: Optional[str] = None,
                     material_id: Optional[str] = None) -> ParseResult:
    """Fetch `url` through the polite fetcher and parse it. Raises the fetcher's errors."""
    resp = fetcher.get(url)
    when = retrieved_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return parse_product_page(resp.text, url, when, material_id)
