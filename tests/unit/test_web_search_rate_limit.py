# Cursor Bite — Web Search Rate Limit Tests
# ============================================================
# Search is the one action that leaves the machine, and DuckDuckGo's
# HTML endpoint is free and unauthenticated — hammering it gets the
# user's IP throttled or blocked, which looks to them like Cursor Bite
# being broken. So the provider spaces requests out.
#
# The limiter's state is a MODULE-LEVEL timestamp, not an instance
# attribute, and that is deliberate: the remote host rate-limits by IP,
# so the budget belongs to the process, not to whichever provider
# object a caller happens to be holding. The tests below pin both that
# scope and the `global` statement that makes the assignment stick —
# without it the write would land on a function-local name and the
# limiter would silently pass every request straight through.
#
# The clock is faked, so this suite spends no real time waiting and
# makes no network request.

import pytest

from infrastructure.search import web_search as ws


# ── Fakes ─────────────────────────────────────────────────────────────


class FakeClock:
    """Stands in for the `time` module inside web_search.

    Time only advances when something sleeps, which makes "did the
    limiter wait, and for how long" directly observable.
    """

    def __init__(self, start: float = 1000.0) -> None:
        self.now = start
        self.sleeps: list[float] = []

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds

    def advance(self, seconds: float) -> None:
        """Move the clock without recording a sleep (time passing on its own)."""
        self.now += seconds


@pytest.fixture()
def clock(monkeypatch):
    """Replace web_search's view of time, and reset the limiter."""
    fake = FakeClock()
    monkeypatch.setattr(ws, "time", fake)
    # Module-level state survives between tests; monkeypatch puts the
    # real value back afterwards.
    monkeypatch.setattr(ws, "_last_request_time", 0.0)
    return fake


@pytest.fixture()
def provider(monkeypatch):
    """A provider that believes it is online and never fetches anything."""
    p = ws.DuckDuckGoSearchProvider()
    p._validated = True
    p._available = True

    fetches: list[tuple[str, int]] = []

    def fake_fetch(query, max_results):
        fetches.append((query, max_results))
        return [{"title": "A hit", "url": "https://example.com", "snippet": "…"}]

    monkeypatch.setattr(p, "_fetch_results", fake_fetch)
    p.fetches = fetches
    return p


# ── Spacing between requests ──────────────────────────────────────────


class TestRequestSpacing:
    def test_first_search_does_not_wait(self, clock, provider):
        provider.search("first query")
        assert clock.sleeps == []

    def test_back_to_back_searches_wait_out_the_interval(self, clock, provider):
        provider.search("first query")
        provider.search("second query")

        assert len(clock.sleeps) == 1
        assert clock.sleeps[0] == pytest.approx(ws._MIN_REQUEST_INTERVAL)

    def test_only_the_remaining_time_is_waited(self, clock, provider):
        """Most of the interval having passed already must not cost a full wait."""
        provider.search("first query")
        clock.advance(0.4)

        provider.search("second query")

        assert clock.sleeps == [pytest.approx(ws._MIN_REQUEST_INTERVAL - 0.4)]

    def test_no_wait_once_the_interval_has_passed(self, clock, provider):
        provider.search("first query")
        clock.advance(ws._MIN_REQUEST_INTERVAL + 0.1)

        provider.search("second query")

        assert clock.sleeps == []

    def test_the_limiter_is_not_a_one_shot(self, clock, provider):
        """Every request after the first is spaced, not just the second."""
        provider.search("one")
        provider.search("two")
        provider.search("three")

        assert len(clock.sleeps) == 2

    def test_every_search_still_reaches_the_endpoint(self, clock, provider):
        provider.search("one")
        provider.search("two")

        assert [q for q, _ in provider.fetches] == ["one", "two"]


# ── Limiter state ─────────────────────────────────────────────────────


class TestLimiterState:
    def test_timestamp_persists_across_calls(self, clock, provider):
        """Regression guard for the missing-`global` bug.

        Without `global _last_request_time`, the assignment in search()
        creates a function-local and the module value stays at 0.0 —
        making every subsequent request look ancient and the limiter a
        no-op.
        """
        provider.search("first query")

        assert ws._last_request_time == pytest.approx(clock.now)
        assert ws._last_request_time != 0.0

    def test_timestamp_moves_forward_with_each_request(self, clock, provider):
        provider.search("one")
        first = ws._last_request_time

        provider.search("two")

        assert ws._last_request_time > first

    def test_budget_is_shared_across_provider_instances(self, clock, monkeypatch):
        """The remote host limits by IP, so the budget is per-process.

        Two provider objects must not each get their own allowance.
        """
        def make():
            p = ws.DuckDuckGoSearchProvider()
            p._validated = True
            p._available = True
            monkeypatch.setattr(p, "_fetch_results", lambda q, m: [])
            return p

        make().search("from the first provider")
        make().search("from the second provider")

        assert len(clock.sleeps) == 1

    def test_module_singleton_shares_the_same_budget(self, clock, monkeypatch):
        monkeypatch.setattr(ws.web_search, "_validated", True)
        monkeypatch.setattr(ws.web_search, "_available", True)
        monkeypatch.setattr(ws.web_search, "_fetch_results", lambda q, m: [])

        ws.web_search.search("one")
        ws.web_search.search("two")

        assert len(clock.sleeps) == 1


# ── Requests that never go out ────────────────────────────────────────


class TestShortCircuits:
    def test_blank_query_does_not_spend_the_budget(self, clock, provider):
        """A rejected query must not make the next real search wait."""
        result = provider.search("   ")

        assert result.success is False
        assert clock.sleeps == []
        assert provider.fetches == []
        assert ws._last_request_time == 0.0

    def test_empty_query_is_rejected(self, clock, provider):
        result = provider.search("")

        assert result.success is False
        assert result.error
        assert provider.fetches == []

    def test_unavailable_provider_does_not_spend_the_budget(self, clock, monkeypatch):
        offline = ws.DuckDuckGoSearchProvider()
        offline._validated = True
        offline._available = False

        result = offline.search("a real query")

        assert result.success is False
        assert "internet" in result.error.lower()
        assert clock.sleeps == []
        assert ws._last_request_time == 0.0

    def test_availability_is_not_probed_on_import_or_construction(self, monkeypatch):
        """No network request may happen before the first real call."""
        def explode(*args, **kwargs):
            raise AssertionError("network touched during construction")

        monkeypatch.setattr(ws.requests, "get", explode)

        fresh = ws.DuckDuckGoSearchProvider()

        assert fresh._validated is False
        assert fresh._available is None
        assert fresh.name()

    def test_invalidate_forces_a_re_probe(self, provider):
        """Connectivity is the one status that routinely changes mid-session."""
        assert provider.is_available() is True

        provider.invalidate()

        assert provider._validated is False
        assert provider._available is None


# ── Result shape ──────────────────────────────────────────────────────


class TestResultShape:
    def test_hits_are_returned_with_the_query(self, clock, provider):
        result = provider.search("python asyncio")

        assert result.success
        assert result.query == "python asyncio"
        assert result.results[0]["title"] == "A hit"

    def test_no_hits_is_a_success_with_no_results(self, clock, provider, monkeypatch):
        monkeypatch.setattr(provider, "_fetch_results", lambda q, m: [])

        result = provider.search("asdkjhasdkjh")

        assert result.success
        assert result.results == []
        assert result.data

    def test_fetch_failure_is_reported_not_raised(self, clock, provider, monkeypatch):
        def explode(query, max_results):
            raise RuntimeError("connection reset")

        monkeypatch.setattr(provider, "_fetch_results", explode)

        result = provider.search("python asyncio")

        assert result.success is False
        assert result.error

    def test_max_results_is_passed_through(self, clock, provider):
        provider.search("python asyncio", max_results=3)

        assert provider.fetches == [("python asyncio", 3)]
