# Cursor Bite — Sensitive Data Detector
# ============================================================
# Detects sensitive information in text that should NOT be sent
# to external services without user consent.
#
# Detected patterns:
#   - Email addresses
#   - Phone numbers (various formats)
#   - API keys (common patterns)
#   - Passwords (in context)
#   - Access tokens
#   - Credit card numbers (Luhn-validated)
#   - Private URLs (localhost, internal IPs)
#   - Obvious credentials (key=value patterns)
#   - Secrets (AWS keys, GitHub tokens, etc.)

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

from utils.logger import get_logger

logger = get_logger("infrastructure.privacy.detector")


# ── Sensitive Data Types ───────────────────────────────────────────

class SensitiveType(Enum):
    """Types of sensitive information that can be detected."""

    EMAIL = "email"
    PHONE = "phone"
    API_KEY = "api_key"
    PASSWORD = "password"
    ACCESS_TOKEN = "access_token"
    CREDIT_CARD = "credit_card"
    PRIVATE_URL = "private_url"
    CREDENTIAL_PAIR = "credential_pair"
    AWS_KEY = "aws_key"
    GITHUB_TOKEN = "github_token"
    IP_ADDRESS = "ip_address"
    UNKNOWN = "unknown"


@dataclass
class SensitiveMatch:
    """A match of sensitive information in text."""

    sensitive_type: SensitiveType
    text: str
    start: int
    end: int
    description: str = ""


# ── Sensitive Data Detector ────────────────────────────────────────

class SensitiveDataDetector:
    """Detects sensitive information in text.

    This detector uses pattern matching to identify common types
    of sensitive data that should be protected from external processing.
    """

    def __init__(self) -> None:
        self._patterns: list[tuple[SensitiveType, re.Pattern, str]] = []
        self._build_patterns()

    # ── Pattern Building ────────────────────────────────────────

    def _build_patterns(self) -> None:
        """Build all detection patterns."""

        # Email addresses
        self._add_pattern(
            SensitiveType.EMAIL,
            re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
            "Email address detected",
        )

        # Phone numbers (various international formats)
        phone_patterns = [
            # US/Canada: (123) 456-7890, 123-456-7890, 123.456.7890
            r"\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b",
            # International: +XX XXXXX XXXXXX
            r"\+\d{1,3}[-.\s]?\d{2,4}[-.\s]?\d{3,4}[-.\s]?\d{3,4}",
            # Generic digit sequences that look like phone numbers
            r"\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b",
        ]
        combined_phone = "|".join(f"({p})" for p in phone_patterns)
        self._add_pattern(
            SensitiveType.PHONE,
            re.compile(combined_phone),
            "Phone number detected",
        )

        # API Keys (various services)
        # AWS Access Key ID: AKIAIOSFODNN7EXAMPLE
        self._add_pattern(
            SensitiveType.AWS_KEY,
            re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
            "AWS Access Key ID detected",
        )

        # Generic API key patterns
        # NOTE: value min-length is intentionally short (4) because the
        # keyword itself (api_key/apikey/...) is what narrows this down —
        # requiring 16+ chars caused real "API_KEY=abc123"-style values to
        # be silently missed.
        self._add_pattern(
            SensitiveType.API_KEY,
            re.compile(
                r"""(?i)\b(
                    api[_-]?key|apikey|api_secret|api[_-]?secret
                )\s*[=:]\s*["']?([A-Za-z0-9_\-]{4,})["']?
                """,
                re.VERBOSE,
            ),
            "API key pattern detected",
        )

        # Access / bearer tokens (various formats), including a bare
        # "token=..." assignment. Value min-length lowered to 4 for the
        # same reason as API_KEY above — the keyword does the narrowing.
        self._add_pattern(
            SensitiveType.ACCESS_TOKEN,
            re.compile(
                r"""(?i)\b(
                    access[_-]?token|auth[_-]?token|[a-z_]*token|bearer\s+[A-Za-z0-9\-._~+/]+
                )\s*[=:]\s*["']?([A-Za-z0-9\-._~+/]{4,})["']?
                """,
                re.VERBOSE,
            ),
            "Access token detected",
        )

        # GitHub tokens
        self._add_pattern(
            SensitiveType.GITHUB_TOKEN,
            re.compile(r"\bghp_[A-Za-z0-9]{36}\b"),
            "GitHub personal access token detected",
        )

        # Credit card numbers (basic pattern + Luhn check)
        self._add_pattern(
            SensitiveType.CREDIT_CARD,
            re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"),
            "Credit card number pattern detected",
        )

        # Passwords in context. Value min-length lowered from 8 to 4 —
        # the 8-char floor caused real "password=secret"-style values
        # (6 chars) to be silently missed.
        self._add_pattern(
            SensitiveType.PASSWORD,
            re.compile(
                r"""(?i)\b(
                    password|passwd|pwd|secret|private[_-]?key
                )\s*[=:]\s*["']?([^\s"']{4,})["']?
                """,
                re.VERBOSE,
            ),
            "Password/credential pattern detected",
        )

        # Private IP addresses
        self._add_pattern(
            SensitiveType.IP_ADDRESS,
            re.compile(r"\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|127\.\d{1,3}\.\d{1,3}\.\d{1,3})\b"),
            "Private IP address detected",
        )

        # localhost URLs
        self._add_pattern(
            SensitiveType.PRIVATE_URL,
            re.compile(r"\b(?:http://)?localhost(?::\d+)?(?:/[^\s]*)?", re.IGNORECASE),
            "Localhost URL detected",
        )

        # Credential pairs: any VARNAME=VALUE / VARNAME: VALUE where the
        # value itself looks like a secret (sk-/pk- prefixed, "secret...",
        # or a long base64-ish blob), regardless of the variable name.
        # BUG FIXED: was `[=:]=` which only matched literal "==" or ":=",
        # so ordinary "KEY=value" / "KEY: value" assignments never matched
        # this rule at all. Correct separator is `[=:]`.
        self._add_pattern(
            SensitiveType.CREDENTIAL_PAIR,
            re.compile(
                r"""\b([A-Za-z_][A-Za-z0-9_]*)\s*[=:]\s*["']?(sk-[A-Za-z0-9]+|pk-[A-Za-z0-9]+|secret[A-Za-z0-9]+|[A-Za-z0-9+/]{40,})["']?
                """,
                re.VERBOSE,
            ),
            "Credential pair detected",
        )

    def _add_pattern(
        self,
        sensitive_type: SensitiveType,
        pattern: re.Pattern,
        description: str,
    ) -> None:
        """Add a detection pattern."""
        self._patterns.append((sensitive_type, pattern, description))

    # ── Detection ───────────────────────────────────────────────

    def detect(self, text: str) -> list[SensitiveMatch]:
        """Detect all sensitive information in the given text.

        Args:
            text: Text to scan for sensitive information.

        Returns:
            List of SensitiveMatch objects for each detection.
        """
        if not text:
            return []

        matches: list[SensitiveMatch] = []
        seen_ranges: list[tuple[int, int]] = []

        for sensitive_type, pattern, description in self._patterns:
            for match in pattern.finditer(text):
                start, end = match.start(), match.end()

                # Skip if this range overlaps with an already-found match
                if self._overlaps_any(start, end, seen_ranges):
                    continue

                seen_ranges.append((start, end))

                matched_text = match.group(0)

                # For credit cards, validate with Luhn check
                if sensitive_type == SensitiveType.CREDIT_CARD:
                    digits = re.sub(r"\D", "", matched_text)
                    if not self._luhn_check(digits):
                        continue  # Not a valid credit card number

                matches.append(SensitiveMatch(
                    sensitive_type=sensitive_type,
                    text=matched_text,
                    start=start,
                    end=end,
                    description=description,
                ))

        return matches

    def has_sensitive_data(self, text: str) -> bool:
        """Quick check: does the text contain any sensitive data?"""
        return len(self.detect(text)) > 0

    def get_sensitive_types(self, text: str) -> list[SensitiveType]:
        """Get the types of sensitive data found in text."""
        matches = self.detect(text)
        return list(dict.fromkeys(m.sensitive_type for m in matches))  # unique, ordered

    def redact(self, text: str) -> str:
        """Redact all sensitive information from text.

        Replaces sensitive data with [REDACTED] markers.
        """
        if not text:
            return text

        matches = self.detect(text)

        # Sort by position (descending) to replace from end to start
        matches.sort(key=lambda m: m.start, reverse=True)

        result = text
        for match in matches:
            replacement = f"[{match.sensitive_type.value.upper()}]"
            result = result[:match.start] + replacement + result[match.end:]

        return result

    # ── Helpers ─────────────────────────────────────────────────

    def _overlaps_any(self, start: int, end: int, ranges: list[tuple[int, int]]) -> bool:
        """Check if a range overlaps with any existing range."""
        for r_start, r_end in ranges:
            if start < r_end and end > r_start:
                return True
        return False

    @staticmethod
    def _luhn_check(digits: str) -> bool:
        """Validate a number using the Luhn algorithm.

        Used to verify credit card numbers.
        """
        if not digits or len(digits) < 13 or len(digits) > 19:
            return False

        try:
            digits = [int(d) for d in digits]
        except ValueError:
            return False

        # Luhn algorithm
        checksum = 0
        parity = len(digits) % 2

        for i, digit in enumerate(digits):
            if i % 2 == parity:
                digit *= 2
                if digit > 9:
                    digit -= 9
            checksum += digit

        return checksum % 10 == 0


# ── Module-level instance ──────────────────────────────────────────

sensitive_detector = SensitiveDataDetector()
"""Global sensitive data detector instance."""
