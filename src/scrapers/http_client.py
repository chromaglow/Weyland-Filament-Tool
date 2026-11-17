"""Polite HTTP fetch layer.

Honours robots.txt, enforces a per-host minimum interval between live
requests, identifies itself with a generic client name, and keeps an on-disk
response cache (with an offline mode that serves only from cache).

Deliberately does NOT do any bot-detection evasion: no header rotation, no
proxies, no headless browsers, no captcha handling.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Optional
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

try:
    from src import __version__
except Exception:  # pragma: no cover
    __version__ = "0"

CLIENT_NAME = "WeylandFilamentTool"
DEFAULT_MIN_INTERVAL = 5.0
DEFAULT_TTL = 7 * 24 * 3600
DEFAULT_TIMEOUT = 30.0
MAX_REDIRECTS = 5


class FetchError(Exception):
    """A request could not be completed."""


class RobotsDisallowedError(FetchError):
    """robots.txt forbids (or could not be confirmed to allow) the URL."""


class OfflineCacheMissError(FetchError):
    """Offline mode and the URL is not in the cache."""


@dataclass
class TransportResponse:
    status: int
    body: bytes
    location: Optional[str] = None  # Location header of a 3xx; the fetcher follows it


@dataclass
class Response:
    url: str
    status: int
    body: bytes
    from_cache: bool = False

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")


Transport = Callable[[str, Dict[str, str], float], TransportResponse]


def default_cache_dir() -> Path:
    """User cache dir, never inside the repo."""
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_CACHE_HOME")
    root = Path(base) if base else Path.home() / ".cache"
    return root / CLIENT_NAME / "http-cache"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Hand 3xx back to the caller instead of following it."""

    def redirect_request(self, *args, **kwargs):
        return None


def open_no_redirect(req: urllib.request.Request, timeout: float):
    """urlopen that never follows redirects: a 3xx surfaces as urllib.error.HTTPError."""
    return urllib.request.build_opener(_NoRedirect).open(req, timeout=timeout)


def urllib_transport(url: str, headers: Dict[str, str], timeout: float) -> TransportResponse:
    """Default transport: plain urllib, honest headers only, no automatic redirects."""
    req = urllib.request.Request(url, headers=headers)
    try:
        with open_no_redirect(req, timeout) as resp:
            return TransportResponse(resp.status, resp.read())
    except urllib.error.HTTPError as e:
        return TransportResponse(e.code, e.read() or b"", e.headers.get("Location"))
    except (urllib.error.URLError, OSError) as e:
        raise FetchError(f"network error for {url}: {e}") from e


class PoliteFetcher:
    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        ttl: float = DEFAULT_TTL,
        min_interval: float = DEFAULT_MIN_INTERVAL,
        offline: bool = False,
        transport: Optional[Transport] = None,
        clock: Callable[[], float] = time.time,
        sleep: Callable[[float], None] = time.sleep,
        user_agent: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        self.cache_dir = Path(cache_dir) if cache_dir else default_cache_dir()
        self.ttl = ttl
        self.min_interval = min_interval
        self.offline = offline
        self.transport = transport or urllib_transport
        self.clock = clock
        self.sleep = sleep
        self.user_agent = user_agent or f"{CLIENT_NAME}/{__version__}"
        self.timeout = timeout
        self._last_request: Dict[str, float] = {}
        self._robots: Dict[str, Optional[RobotFileParser]] = {}

    # -- public -----------------------------------------------------------
    def get(self, url: str) -> Response:
        parts = urlparse(url)
        if parts.scheme not in ("http", "https") or not parts.netloc:
            raise FetchError(f"unsupported URL: {url}")

        cached = self._cache_read(url, allow_expired=self.offline)
        if cached is not None:
            return cached
        if self.offline:
            raise OfflineCacheMissError(f"offline mode and not cached: {url}")

        resp = self._fetch_following(url)
        self._cache_write(url, resp)
        return Response(url, resp.status, resp.body, from_cache=False)

    def _fetch_following(self, url: str) -> TransportResponse:
        """Each hop (original URL and every redirect target) is a new polite request:
        robots.txt and the per-host interval apply to it. Failing closed on loops,
        too many hops and non-http(s) targets."""
        seen = set()
        for _ in range(MAX_REDIRECTS + 1):
            if url in seen:
                raise FetchError(f"redirect loop at {url}")
            seen.add(url)
            parts = urlparse(url)
            if parts.scheme not in ("http", "https") or not parts.netloc:
                raise FetchError(f"unsupported URL: {url}")
            if not self._allowed(parts, url):
                raise RobotsDisallowedError(f"robots.txt disallows fetching {url}")
            resp = self._live(parts.netloc, url)
            if resp.status in (301, 302, 303, 307, 308) and resp.location:
                url = urljoin(url, resp.location)
                continue
            if resp.status != 200:
                raise FetchError(f"HTTP {resp.status} for {url}")
            return resp
        raise FetchError(f"too many redirects (more than {MAX_REDIRECTS}) from {url}")

    # -- live requests ----------------------------------------------------
    def _live(self, host: str, url: str) -> TransportResponse:
        last = self._last_request.get(host)
        if last is not None:
            wait = self.min_interval - (self.clock() - last)
            if wait > 0:
                self.sleep(wait)
        try:
            return self.transport(
                url, {"User-Agent": self.user_agent, "Accept": "*/*"}, self.timeout
            )
        finally:
            self._last_request[host] = self.clock()

    # -- robots -----------------------------------------------------------
    def _allowed(self, parts, url: str) -> bool:
        host = parts.netloc
        if host not in self._robots:
            self._robots[host] = self._load_robots(parts)
        parser = self._robots[host]
        if parser is None:
            return False
        return parser.can_fetch(self.user_agent, url)

    def _load_robots(self, parts) -> Optional[RobotFileParser]:
        robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
        try:
            resp = self._live(parts.netloc, robots_url)
        except FetchError:
            # Fail closed (the page is not fetched) but keep the real reason and type, e.g.
            # RateLimitError; nothing is cached, so a later call retries.
            raise
        parser = RobotFileParser()
        if resp.status == 200:
            parser.parse(resp.body.decode("utf-8", errors="replace").splitlines())
        elif 400 <= resp.status < 500:
            parser.parse([])  # no robots.txt: everything allowed
        else:
            return None  # server trouble: be conservative
        return parser

    # -- cache ------------------------------------------------------------
    def _paths(self, url: str):
        key = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{key}.json", self.cache_dir / f"{key}.body"

    def _cache_read(self, url: str, allow_expired: bool) -> Optional[Response]:
        meta_p, body_p = self._paths(url)
        try:
            meta = json.loads(meta_p.read_text(encoding="utf-8"))
            body = body_p.read_bytes()
        except (OSError, ValueError):
            return None
        if not allow_expired and self.clock() - meta["fetched_at"] > self.ttl:
            return None
        return Response(url, meta.get("status", 200), body, from_cache=True)

    def _cache_write(self, url: str, resp: TransportResponse) -> None:
        meta_p, body_p = self._paths(url)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        body_p.write_bytes(resp.body)
        meta_p.write_text(
            json.dumps({"url": url, "status": resp.status, "fetched_at": self.clock()}),
            encoding="utf-8",
        )
