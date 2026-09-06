# Cursor Bite — Search Provider Tests
# ============================================================
# Tests for DuckDuckGo error classification, status taxonomy,
# and result handling.

from unittest.mock import MagicMock, patch
import pytest
import requests

from infrastructure.search.web_search import DuckDuckGoSearchProvider


def test_search_empty_query():
    """Verify empty query fails with an actionable error."""
    provider = DuckDuckGoSearchProvider()
    res = provider.search("")
    assert not res.success
    assert "No search query provided" in res.error


def test_search_timeout_error():
    """Verify Timeout raises and maps to 'timeout' status."""
    provider = DuckDuckGoSearchProvider()
    provider._ensure_ready = MagicMock(return_value=True)

    with patch.object(provider, "_fetch_results", side_effect=requests.exceptions.Timeout("Read timeout")):
        res = provider.search("python asyncio")
        assert not res.success
        assert res.metadata.get("status") == "timeout"
        assert "timed out" in res.error.lower()


def test_search_connection_error():
    """Verify ConnectionError maps to 'network_unavailable' status."""
    provider = DuckDuckGoSearchProvider()
    provider._ensure_ready = MagicMock(return_value=True)

    with patch.object(provider, "_fetch_results", side_effect=requests.exceptions.ConnectionError("Offline")):
        res = provider.search("python asyncio")
        assert not res.success
        assert res.metadata.get("status") == "network_unavailable"
        assert "check your internet" in res.error.lower() or "reach duckduckgo" in res.error.lower()


def test_search_rate_limited():
    """Verify 429 response maps to 'rate_limited' status."""
    provider = DuckDuckGoSearchProvider()
    provider._ensure_ready = MagicMock(return_value=True)

    with patch.object(provider, "_fetch_results", side_effect=Exception("HTTP 429 RateLimitException")):
        res = provider.search("python asyncio")
        assert not res.success
        assert res.metadata.get("status") == "rate_limited"
        assert "rate limited" in res.error.lower()


def test_search_empty_results():
    """Verify zero results map to status 'empty'."""
    provider = DuckDuckGoSearchProvider()
    provider._ensure_ready = MagicMock(return_value=True)

    with patch.object(provider, "_fetch_results", return_value=([], None, "empty")):
        res = provider.search("xyznonexistentterm123456789")
        assert res.success
        assert res.metadata.get("status") == "empty"
        assert len(res.results) == 0
        assert "No results found" in res.data


def test_search_success():
    """Verify valid results return success with count."""
    provider = DuckDuckGoSearchProvider()
    provider._ensure_ready = MagicMock(return_value=True)

    mock_results = [
        {"title": "Result 1", "url": "https://example.com/1", "snippet": "Snippet 1"},
        {"title": "Result 2", "url": "https://example.com/2", "snippet": "Snippet 2"},
    ]
    with patch.object(provider, "_fetch_results", return_value=(mock_results, None, "success")):
        res = provider.search("python programming")
        assert res.success
        assert res.metadata.get("status") == "success"
        assert len(res.results) == 2
