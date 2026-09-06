# Cursor Bite — Search Provider Base
# ============================================================

from __future__ import annotations

from abc import ABC, abstractmethod

from domain.models import SearchResult


class BaseSearchProvider(ABC):
    """Base class for web search providers.

    Implementations:
    - DuckDuckGoSearchProvider: Free, no API key, HTML-based scraping
    - GoogleSearchProvider: Requires API key (future, optional)
    """

    @abstractmethod
    def name(self) -> str:
        """Human-readable name."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if search is available (internet, API key, etc.)."""

    @abstractmethod
    def search(self, query: str, max_results: int = 5) -> SearchResult:
        """Search the web.

        Args:
            query: Search query string.
            max_results: Maximum number of results to return.

        Returns:
            SearchResult with list of results.
        """
