"""Source B adapter: community OrcaSlicer/Bambu filament profile JSON.

Reads a profile file from raw.githubusercontent.com (through PoliteFetcher only),
follows its `inherits` chain in the same folder, and emits SourcedValue entries
(status "published", kind COMMUNITY_REPO) keyed by Bambu key names. Keys outside
the Bambu filament catalogue are kept in `CommunityProfile.extras`.

Treat fetched JSON as data only. No bot-detection evasion lives here.

Note: src/importers (wft-3abc8e.9) also resolves `inherits`, against local system
presets. The two resolvers are intentionally independent for now; QA may merge them.
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import quote, unquote, urlparse

from src.data.sourced import CollectedSettings, SourceKind, SourcedValue
from src.generator.bambu_keys import load_catalogue
from src.scrapers.http_client import FetchError, PoliteFetcher, TransportResponse

DEFAULT_REF = "main"
DEFAULT_MAX_DEPTH = 8
TOKEN_ENV = "WFT_GITHUB_TOKEN"
GITHUB_HOSTS = {"raw.githubusercontent.com", "api.github.com"}

# Structural/identity keys of a profile file: not settings, not extras.
_META_KEYS = {"type", "name", "inherits", "from", "instantiation", "setting_id", "filament_id", "include"}

# ASSUMPTION: many values are per-nozzle-variant arrays (e.g. ["0.98","0.985"]).
# Index 0 is treated as the standard variant. Unverified against a local preset.
_VARIANT_INDEX = 0

_NUM = re.compile(r"^-?\d+(\.\d+)?$")


class InheritanceError(FetchError):
    pass


class ParentNotFoundError(InheritanceError):
    """An `inherits` parent could not be fetched."""


class InheritanceDepthError(InheritanceError):
    """Chain is deeper than max_depth, or loops."""


class RateLimitError(FetchError):
    """GitHub rate limit exhausted; try again after the reset time."""


@dataclass
class CommunityProfile:
    settings: CollectedSettings
    extras: Dict[str, Any] = field(default_factory=dict)  # raw JSON values of non-catalogue keys
    chain: List[str] = field(default_factory=list)  # profile names, leaf first


def raw_url(repo: str, path: str, ref: str = DEFAULT_REF) -> str:
    return f"https://raw.githubusercontent.com/{repo}/{ref}/{quote(path, safe='/')}"


def _split_url(url: str):
    """(source_id, directory url) for a raw URL; plain URL as id otherwise."""
    p = urlparse(url)
    parts = [unquote(s) for s in p.path.split("/")]
    if p.netloc == "raw.githubusercontent.com" and len(parts) >= 5:
        repo = "/".join(parts[1:3])
        return f"{repo}:{'/'.join(parts[4:])}"
    return url


def _normalise_input(source: str) -> str:
    if source.startswith(("http://", "https://")):
        return source
    repo, _, path = source.partition(":")
    if not path:
        raise ValueError("expected a raw URL or 'owner/repo:path/to/file.json'")
    return raw_url(repo, path)


def _usable(value: Any) -> Optional[str]:
    """Standard-variant text of a profile value, or None for absent / "nil"."""
    if isinstance(value, list):
        if len(value) <= _VARIANT_INDEX:
            return None
        value = value[_VARIANT_INDEX]
    if value is None or isinstance(value, (dict, list)):
        return None
    text = str(value)
    return None if text == "nil" else text


def _convert(text: str):
    if _NUM.match(text):
        return float(text) if "." in text else int(text)
    return text


def collect_profile(
    fetcher: PoliteFetcher,
    source: str,
    *,
    retrieved_at: Optional[str] = None,
    max_depth: int = DEFAULT_MAX_DEPTH,
) -> CommunityProfile:
    """Fetch a profile and its parents and return values with provenance.

    `source` is a raw file URL or 'owner/repo:path/to/file.json'. Parents are
    fetched from the same folder as `<inherits>.json`, one polite fetch each.
    """
    leaf_url = _normalise_input(source)
    retrieved_at = retrieved_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    folder = leaf_url.rsplit("/", 1)[0]
    source_id = _split_url(leaf_url)

    docs: List[tuple] = []  # (name, url, doc), leaf first
    seen = set()
    url, child = leaf_url, None
    while True:
        try:
            doc = json.loads(fetcher.get(url).text)
        except FetchError as e:
            if child is not None and "HTTP 404" in str(e):
                raise ParentNotFoundError(f"parent profile {unquote(url)} (inherited by {child!r}) not found") from e
            raise
        if not isinstance(doc, dict):
            raise InheritanceError(f"{url} is not a JSON object")
        name = doc.get("name") or unquote(url.rsplit("/", 1)[1]).removesuffix(".json")
        if name in seen:
            raise InheritanceDepthError(f"inherits loop at {name!r}")
        seen.add(name)
        docs.append((name, url, doc))
        if len(docs) > max_depth:
            raise InheritanceDepthError(f"inherits chain deeper than {max_depth} at {name!r}")
        parent = doc.get("inherits")
        if not parent:
            break
        child = name
        url = f"{folder}/{quote(parent, safe='')}.json"

    catalogue = set(load_catalogue()["filament"])
    settings = CollectedSettings(material_id=docs[0][0], name=docs[0][0])
    extras: Dict[str, Any] = {}
    resolved = set()
    for depth, (name, url, doc) in enumerate(docs):
        for key, value in doc.items():
            if key in _META_KEYS or key in resolved:
                continue
            if key not in catalogue:
                extras[key] = value  # nearest file wins; kept raw, not dropped
                resolved.add(key)
                continue
            text = _usable(value)
            if text is None:
                continue  # "nil"/absent here: inherit from a parent
            resolved.add(key)
            settings.add(SourcedValue(
                key=key,
                value=_convert(text),
                source_id=source_id,
                source_kind=SourceKind.COMMUNITY_REPO,
                source_url=url,
                status="published",
                retrieved_at=retrieved_at,
                raw=text,
                note=f"inherited from {name}" if depth else None,
            ))
    return CommunityProfile(settings=settings, extras=extras, chain=[d[0] for d in docs])


def github_transport(env_var: str = TOKEN_ENV) -> Callable[[str, Dict[str, str], float], TransportResponse]:
    """Transport for PoliteFetcher that adds an optional token and honours rate limits.

    The token is read from the environment at call time, sent only to GitHub
    hosts, and never logged or put in an error message. If GitHub reports the
    limit exhausted the call raises RateLimitError with the reset time; nothing sleeps.
    """

    def transport(url: str, headers: Dict[str, str], timeout: float) -> TransportResponse:
        headers = dict(headers)
        token = os.environ.get(env_var)
        if token and urlparse(url).hostname in GITHUB_HOSTS:
            headers["Authorization"] = f"Bearer {token}"
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status, body, hdrs = resp.status, resp.read(), resp.headers
        except urllib.error.HTTPError as e:
            status, body, hdrs = e.code, e.read() or b"", e.headers
        except (urllib.error.URLError, OSError) as e:
            raise FetchError(f"network error for {url}: {e}") from e
        if status in (403, 429):
            remaining = hdrs.get("X-RateLimit-Remaining")
            retry_after = hdrs.get("Retry-After")
            if remaining == "0" or retry_after:
                reset = hdrs.get("X-RateLimit-Reset")
                when = f"resets at epoch {reset}" if reset else f"retry after {retry_after}s"
                raise RateLimitError(f"GitHub rate limit reached for {url}; {when}")
        return TransportResponse(status, body)

    return transport
