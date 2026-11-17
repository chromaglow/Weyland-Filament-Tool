"""Source A adapter: manufacturer product page (Timeplast TimeMass guide).

Fetches a product URL through PoliteFetcher and parses the printing guide into
SourcedValue candidates (status "published", Bambu key names, ranges as
2-tuples). Matching is on label text, never on CSS class names. Numbered guide
items that are not mapped are logged and returned in `unmapped`, never guessed.

Field map: docs/research/online-sources.md ("Source A"). No bed temperatures
are published by this source, so none are emitted.
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
    for m in _ITEM.finditer(_page_text(page)):
        label = m.group("label").strip()
        ident = (m.group("num"), label.lower())
        if ident in seen:  # page carries a desktop and a mobile copy
            continue
        seen.add(ident)
        value_text = _DESC_SPLIT.split(m.group("body").strip(), maxsplit=1)[0].strip()
        handler = _LABELS.get(label.lower())
        mapped = handler(value_text) if handler else []
        if not mapped:
            phrase = f"{m.group('num')} {label}: {value_text}"
            result.unmapped.append(phrase)
            logger.warning("Source A: unmapped phrase %r (%s)", phrase, url)
            continue
        for key, value, note in mapped:
            settings.add(SourcedValue(
                key=key, value=value, source_id=SOURCE_ID,
                source_kind=SourceKind.MAKER_PRODUCT_PAGE, source_url=url,
                status="published", retrieved_at=retrieved_at,
                raw=f"{label}: {value_text}", note=note,
            ))
    return result


def collect_from_url(url: str, fetcher: PoliteFetcher, retrieved_at: Optional[str] = None,
                     material_id: Optional[str] = None) -> ParseResult:
    """Fetch `url` through the polite fetcher and parse it. Raises the fetcher's errors."""
    resp = fetcher.get(url)
    when = retrieved_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return parse_product_page(resp.text, url, when, material_id)
