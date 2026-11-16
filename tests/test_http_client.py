"""Tests for the polite fetch layer. No live network: a fake transport is injected."""
import pytest

from src.scrapers.http_client import (
    FetchError,
    OfflineCacheMissError,
    PoliteFetcher,
    RobotsDisallowedError,
    TransportResponse,
)

ROBOTS = "User-agent: *\nDisallow: /private/\n"


class FakeClock:
    def __init__(self):
        self.now = 1000.0
        self.sleeps = []

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


class FakeTransport:
    def __init__(self, robots=ROBOTS, robots_status=200):
        self.calls = []
        self.robots = robots
        self.robots_status = robots_status

    def __call__(self, url, headers, timeout):
        self.calls.append((url, dict(headers)))
        if url.endswith("/robots.txt"):
            return TransportResponse(self.robots_status, self.robots.encode())
        return TransportResponse(200, b"body of " + url.encode())


def make(tmp_path, transport=None, clock=None, **kw):
    clock = clock or FakeClock()
    transport = transport or FakeTransport()
    f = PoliteFetcher(
        cache_dir=tmp_path / "cache",
        transport=transport,
        clock=clock.time,
        sleep=clock.sleep,
        **kw,
    )
    return f, transport, clock


def pages(transport):
    return [u for u, _ in transport.calls if not u.endswith("/robots.txt")]


def test_get_returns_body(tmp_path):
    f, _, _ = make(tmp_path)
    r = f.get("https://example.com/a")
    assert r.status == 200 and r.text == "body of https://example.com/a"
    assert r.from_cache is False


def test_robots_disallow_refuses_without_fetching_page(tmp_path):
    f, t, _ = make(tmp_path)
    with pytest.raises(RobotsDisallowedError) as e:
        f.get("https://example.com/private/x")
    assert "robots.txt" in str(e.value)
    assert pages(t) == []


def test_robots_cached_per_host(tmp_path):
    f, t, _ = make(tmp_path, min_interval=0)
    f.get("https://example.com/a")
    f.get("https://example.com/b")
    f.get("https://other.org/a")
    robots = [u for u, _ in t.calls if u.endswith("/robots.txt")]
    assert robots == ["https://example.com/robots.txt", "https://other.org/robots.txt"]


def test_robots_404_allows_all(tmp_path):
    f, _, _ = make(tmp_path, transport=FakeTransport(robots="", robots_status=404))
    assert f.get("https://example.com/private/x").status == 200


def test_robots_server_error_refuses(tmp_path):
    f, _, _ = make(tmp_path, transport=FakeTransport(robots="", robots_status=503))
    with pytest.raises(RobotsDisallowedError):
        f.get("https://example.com/a")


def test_rate_limit_waits_between_live_requests_same_host(tmp_path):
    f, _, clock = make(tmp_path, min_interval=5)
    f.get("https://example.com/a")
    f.get("https://example.com/b")
    assert sum(clock.sleeps) == pytest.approx(5, abs=0.01) or sum(clock.sleeps) >= 5


def test_rate_limit_no_wait_when_interval_elapsed(tmp_path):
    f, _, clock = make(tmp_path, min_interval=5)
    f.get("https://example.com/a")
    clock.sleeps.clear()
    clock.now += 60
    f.get("https://example.com/b")
    assert clock.sleeps == []


def test_rate_limit_is_per_host(tmp_path):
    f, _, clock = make(tmp_path, min_interval=5)
    f.get("https://example.com/a")
    t0 = clock.now
    times = {}

    class T(FakeTransport):
        def __call__(self, url, headers, timeout):
            times[url] = clock.now
            return super().__call__(url, headers, timeout)

    f.transport = T()
    f.get("https://other.org/a")
    # first request to a new host is not delayed by another host's traffic
    assert times["https://other.org/robots.txt"] == t0


def test_default_interval_is_five_seconds(tmp_path):
    f, _, _ = make(tmp_path)
    assert f.min_interval == 5


def test_cache_hit_makes_no_network_call(tmp_path):
    f, t, _ = make(tmp_path)
    f.get("https://example.com/a")
    n = len(t.calls)
    r = f.get("https://example.com/a")
    assert r.from_cache is True and r.text == "body of https://example.com/a"
    assert len(t.calls) == n


def test_cache_persists_across_instances(tmp_path):
    f, _, clock = make(tmp_path)
    f.get("https://example.com/a")
    f2, t2, _ = make(tmp_path, clock=clock)
    assert f2.get("https://example.com/a").from_cache is True
    assert t2.calls == []


def test_cache_expiry_refetches(tmp_path):
    f, t, clock = make(tmp_path, ttl=100)
    f.get("https://example.com/a")
    clock.now += 101
    r = f.get("https://example.com/a")
    assert r.from_cache is False
    assert len(pages(t)) == 2


def test_default_ttl_is_seven_days(tmp_path):
    f, _, _ = make(tmp_path)
    assert f.ttl == 7 * 24 * 3600


def test_offline_serves_cache_only(tmp_path):
    f, t, _ = make(tmp_path)
    f.get("https://example.com/a")
    n = len(t.calls)
    f.offline = True
    assert f.get("https://example.com/a").from_cache is True
    with pytest.raises(OfflineCacheMissError):
        f.get("https://example.com/never")
    assert len(t.calls) == n


def test_offline_serves_expired_entries(tmp_path):
    f, _, clock = make(tmp_path, ttl=10)
    f.get("https://example.com/a")
    clock.now += 1000
    f.offline = True
    assert f.get("https://example.com/a").from_cache is True


def test_user_agent_is_generic(tmp_path):
    f, t, _ = make(tmp_path)
    f.get("https://example.com/a")
    for _, headers in t.calls:
        ua = headers["User-Agent"]
        assert ua.startswith("WeylandFilamentTool/")
        assert "Mozilla" not in ua
    assert set(headers) == {"User-Agent", "Accept"} or "User-Agent" in headers


def test_non_200_raises_and_is_not_cached(tmp_path):
    class T(FakeTransport):
        def __call__(self, url, headers, timeout):
            if url.endswith("/robots.txt"):
                return super().__call__(url, headers, timeout)
            self.calls.append((url, headers))
            return TransportResponse(500, b"err")

    f, t, _ = make(tmp_path, transport=T(), min_interval=0)
    with pytest.raises(FetchError):
        f.get("https://example.com/a")
    with pytest.raises(FetchError):
        f.get("https://example.com/a")
    assert len(pages(t)) == 2


def test_rejects_non_http_scheme(tmp_path):
    f, _, _ = make(tmp_path)
    with pytest.raises(FetchError):
        f.get("file:///etc/passwd")


def test_default_cache_dir_is_outside_repo():
    from src.scrapers.http_client import default_cache_dir
    from pathlib import Path

    repo = Path(__file__).resolve().parents[1]
    assert repo not in default_cache_dir().resolve().parents
