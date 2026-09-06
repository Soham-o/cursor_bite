# Cursor Bite — Web Search Provider (Free Implementation)
# ============================================================
# Free web search using DuckDuckGo HTML endpoint.
#
# LAZY INITIALIZATION: No network request on import.
# The first call to is_available() or search() triggers a check.
#
# IMPORTANT: DuckDuckGo search requires an internet connection
# and may be rate-limited. This is a best-effort feature.

import logging
import re
import time
from typing import Optional

import requests
from bs4 import BeautifulSoup

from domain.models import SearchResult
from infrastructure.search.base import BaseSearchProvider
from utils.logger import get_logger

logger = get_logger("infrastructure.search.web_search")

# Rate limiting: be respectful to DuckDuckGo's servers
_MIN_REQUEST_INTERVAL = 1.0
_last_request_time: float = 0.0


# ── DuckDuckGo Search Provider ─────────────────────────────────────

class DuckDuckGoSearchProvider(BaseSearchProvider):
    """Free web search using DuckDuckGo's HTML interface.

    No network request is made on __init__ or on is_available()
    until the first actual search is performed.
    """

    def __init__(self) -> None:
        self._available: Optional[bool] = None
        self._validated: bool = False
        self._user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )

    # ── Lazy Validation ─────────────────────────────────────────

    def _ensure_ready(self) -> bool:
        """Lazy check — called on first search, not on import."""
        if self._validated:
            return self._available or False
        self._validated = True

        try:
            response = requests.get(
                "https://duckduckgo.com",
                timeout=5,
                headers={"User-Agent": self._user_agent},
            )
            self._available = response.status_code in (200, 301, 302, 303, 307, 308)
            if self._available:
                logger.info("Web search is available (internet connection detected).")
            else:
                logger.info(f"Web search unavailable (status {response.status_code}).")
            return self._available
        except Exception as e:
            self._available = False
            logger.info(f"Web search unavailable: {e}")
            return False

    # ── Interface Implementation ────────────────────────────────

    def name(self) -> str:
        return "DuckDuckGo Web Search (Free)"

    def is_available(self) -> bool:
        """Check availability. No network call until first search."""
        return self._ensure_ready()

    def search(self, query: str, max_results: int = 5) -> SearchResult:
        """Search the web. Lazy initialization on first call."""
        # `global` is required: without it the assignment below would create a
        # function-local name and the module-level timestamp would stay at 0.0,
        # making the rate limiter a no-op across calls.
        global _last_request_time

        if not query or not query.strip():
            return SearchResult(success=False, error="No search query provided.", query=query)

        if not self._ensure_ready():
            return SearchResult(
                success=False,
                error="Web search is not available. Check your internet connection.",
                query=query,
            )

        # Rate limiting
        now = time.time()
        elapsed = now - _last_request_time
        if elapsed < _MIN_REQUEST_INTERVAL:
            time.sleep(_MIN_REQUEST_INTERVAL - elapsed)
        _last_request_time = time.time()

        try:
            logger.info("Web search initiated.")

            fetch_res = self._fetch_results(query, max_results)
            if isinstance(fetch_res, tuple) and len(fetch_res) == 3:
                results, err_msg, status_code = fetch_res
            elif isinstance(fetch_res, tuple) and len(fetch_res) == 2:
                results, err_msg = fetch_res
                status_code = "success" if results else "empty"
            else:
                results = fetch_res or []
                err_msg = None
                status_code = "success" if results else "empty"

            if err_msg:

                logger.warning(f"Web search returned error: {err_msg} (status: {status_code})")
                return SearchResult(
                    success=False,
                    error=err_msg,
                    query=query,
                    metadata={"status": status_code},
                )

            if results:
                logger.info(f"Web search returned {len(results)} results.")
                return SearchResult(
                    success=True,
                    data=f"Found {len(results)} results.",
                    query=query,
                    results=results,
                    metadata={"status": "success", "count": len(results)},
                )
            else:
                logger.info("Web search returned no results for query.")
                return SearchResult(
                    success=True,
                    data="No results found for your query. Try different or fewer keywords.",
                    query=query,
                    results=[],
                    metadata={"status": "empty"},
                )

        except requests.exceptions.Timeout:
            logger.warning("Web search timed out.")
            return SearchResult(
                success=False,
                error="Search timed out: DuckDuckGo took too long to respond. Please try again.",
                query=query,
                metadata={"status": "timeout"},
            )
        except requests.exceptions.ConnectionError:
            logger.warning("Web search connection failed.")
            return SearchResult(
                success=False,
                error="Search unavailable: Could not reach DuckDuckGo. Check your internet connection.",
                query=query,
                metadata={"status": "network_unavailable"},
            )
        except Exception as e:
            logger.warning(f"Web search failed: {e}")
            err_str = str(e).lower()
            if "429" in err_str or "ratelimit" in err_str or "rate limit" in err_str:
                return SearchResult(
                    success=False,
                    error="Search rate limited: Too many requests sent to DuckDuckGo. Please wait a moment before trying again.",
                    query=query,
                    metadata={"status": "rate_limited"},
                )
            return SearchResult(
                success=False,
                error=f"Search failed: {str(e)}",
                query=query,
                metadata={"status": "provider_failure"},
            )

    # ── Private Implementation ──────────────────────────────────

    def invalidate(self) -> None:
        """Forget the cached availability check so the next call re-probes.

        Used by the Components dialog's "Re-check" button — connectivity
        is the one component status that routinely changes mid-session.
        """
        self._validated = False
        self._available = None

    def _fetch_results(self, query: str, max_results: int) -> tuple[list, Optional[str], str]:
        """Fetch search results using ddgs or fallback HTML parsing.

        Returns:
            (results, error_message, status_code)
        """
        results: list = []

        # Strategy 1: Try modern ddgs library
        try:
            try:
                from ddgs import DDGS
            except ImportError:
                from duckduckgo_search import DDGS

            with DDGS(timeout=10) as ddgs:
                raw_results = list(ddgs.text(query, max_results=max_results))
                for r in raw_results:
                    title = r.get("title", "").strip()
                    url = r.get("href", "").strip()
                    snippet = r.get("body", "").strip()
                    if title and url:
                        results.append({
                            "title": title,
                            "url": url,
                            "snippet": snippet,
                        })

            if results:
                return results, None, "success"

        except Exception as e:
            err_str = str(e).lower()
            if "429" in err_str or "ratelimit" in err_str or "rate limit" in err_str:
                return [], "Search rate limited: DuckDuckGo is receiving too many requests. Please wait a moment.", "rate_limited"
            if "timeout" in err_str:
                return [], "Search timed out: DuckDuckGo took too long to respond.", "timeout"
            if "connection" in err_str or "failed to establish" in err_str or "nodename" in err_str:
                return [], "Search unavailable: Could not reach DuckDuckGo. Check your internet connection.", "network_unavailable"
            logger.debug(f"ddgs search failed, attempting HTML fallback: {e}")

        # Strategy 2: HTML Endpoint fallback
        try:
            url = "https://html.duckduckgo.com/html/"
            params = {"q": query, "format": "html"}
            headers = {
                "User-Agent": self._user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }

            response = requests.get(url, params=params, headers=headers, timeout=10)

            if response.status_code == 429:
                return [], "Search rate limited: Server returned HTTP 429.", "rate_limited"
            elif response.status_code == 202:
                # 202 is an anti-bot challenge page
                logger.warning("DuckDuckGo HTML endpoint returned status 202 (bot challenge).")
                # Try instant answer API fallback before giving up
                api_results = self._fetch_instant_answer(query)
                if api_results:
                    return api_results, None, "success"
                return [], "Search provider temporarily unavailable: Bot challenge encountered. Please wait a moment.", "provider_failure"
            elif response.status_code != 200:
                return [], f"Search provider error: HTTP {response.status_code}", "provider_failure"

            soup = BeautifulSoup(response.text, "html.parser")
            result_links = soup.select("a.result__a")
            for link in result_links[:max_results]:
                title = link.get_text(strip=True)
                href = link.get("href", "")
                if title and href:
                    actual_url = self._extract_url(href)
                    parent = link.find_parent("div", class_=re.compile(r"result|results_links"))
                    snippet = ""
                    if parent:
                        snip_elem = parent.select_one(".result__snippet")
                        if snip_elem:
                            snippet = snip_elem.get_text(strip=True)
                    results.append({
                        "title": title,
                        "url": actual_url,
                        "snippet": snippet,
                    })

            if results:
                return results, None, "success"

        except requests.exceptions.Timeout:
            return [], "Search timed out: DuckDuckGo took too long to respond.", "timeout"
        except requests.exceptions.ConnectionError:
            return [], "Search unavailable: Could not reach DuckDuckGo. Check your internet connection.", "network_unavailable"
        except Exception as e:
            logger.debug(f"HTML fallback failed: {e}")

        # Strategy 3: Instant Answer API fallback
        api_results = self._fetch_instant_answer(query)
        if api_results:
            return api_results, None, "success"

        return [], None, "empty"

    def _fetch_instant_answer(self, query: str) -> list:
        """Fetch results from DuckDuckGo Instant Answer API as a backup."""
        results = []
        try:
            r = requests.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
                timeout=5,
            )
            data = r.json()
            abstract = data.get("AbstractText", "")
            abstract_url = data.get("AbstractURL", "")
            heading = data.get("Heading", query)
            if abstract and abstract_url:
                results.append({
                    "title": heading,
                    "url": abstract_url,
                    "snippet": abstract,
                })
            for topic in data.get("RelatedTopics", [])[:4]:
                if isinstance(topic, dict) and "Text" in topic and "FirstURL" in topic:
                    results.append({
                        "title": topic.get("Text", "").split(" - ")[0],
                        "url": topic.get("FirstURL", ""),
                        "snippet": topic.get("Text", ""),
                    })
        except Exception:
            pass
        return results

    @staticmethod
    def _extract_url(duckduckgo_url: str) -> str:
        """Extract the actual URL from a DuckDuckGo redirect link."""
        match = re.search(r"uddg=([^&]+)", duckduckgo_url)
        if match:
            from urllib.parse import unquote
            return unquote(match.group(1))
        return duckduckgo_url


# ── Module-level instance (lazy — no network on import) ───────────

web_search = DuckDuckGoSearchProvider()
"""Global web search provider instance. No network call on import."""
