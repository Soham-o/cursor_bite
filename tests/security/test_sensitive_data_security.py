# Cursor Bite — Sensitive Data Security Tests
# ============================================================
# These tests verify security properties of the sensitive data
# detector and privacy gateway that go beyond functional correctness:
#
#   1. User content never leaks into log-visible strings (reasons)
#   2. Multiple sensitive types in a single string are all caught
#   3. Redaction is safe: no partial exposure after redaction
#   4. The detector does not short-circuit on the first match —
#      every pattern is checked independently
#   5. Edge cases that could trip up an attacker trying to bypass
#      detection (obfuscation, whitespace, case variants)

import pytest

from infrastructure.privacy.detector import SensitiveDataDetector, SensitiveType
from infrastructure.privacy.gateway import PrivacyGateway
from config.settings import settings


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture()
def detector() -> SensitiveDataDetector:
    return SensitiveDataDetector()


@pytest.fixture()
def gateway() -> PrivacyGateway:
    return PrivacyGateway()


@pytest.fixture()
def clean_settings():
    original = dict(settings._config)
    settings._config = {}
    yield settings
    settings._config = original


# ── No sensitive content in block reasons ─────────────────────────────


class TestNoContentLeakInReasons:
    """The reason strings returned by the gateway (which get logged)
    must never contain the raw sensitive value itself."""

    @pytest.mark.parametrize("secret", [
        "topsecret@example.com",
        "hunter22secret",
        "AKIAIOSFODNN7EXAMPLE",
        "ghp_" + "z" * 36,
    ])
    def test_block_reason_does_not_contain_raw_secret(
        self, clean_settings, gateway, secret
    ):
        clean_settings.set("privacy.offline_mode", False)
        clean_settings.set("privacy.sensitive_data_protection", True)
        result = gateway.evaluate(
            f"Here is my secret: {secret}", requires_external=True
        )
        if result.is_blocked:
            assert secret not in result.reason, (
                f"Secret value leaked into block reason: {secret!r}"
            )


# ── Multiple sensitive types co-detected ──────────────────────────────


class TestMultipleSensitiveTypesDetected:
    """A string containing several sensitive patterns must surface
    ALL of them, not just the first one found."""

    def test_email_and_phone_both_detected(self, detector):
        text = "contact alice@example.com or call 415-555-0100"
        types = detector.get_sensitive_types(text)
        assert SensitiveType.EMAIL in types
        assert SensitiveType.PHONE in types

    def test_api_key_and_password_both_detected(self, detector):
        text = "api_key=abcdef123456 and password=hunter22"
        types = detector.get_sensitive_types(text)
        assert SensitiveType.API_KEY in types
        assert SensitiveType.PASSWORD in types

    def test_aws_key_and_email_both_detected(self, detector):
        text = "Key: AKIAIOSFODNN7EXAMPLE  user: admin@example.com"
        types = detector.get_sensitive_types(text)
        assert SensitiveType.AWS_KEY in types
        assert SensitiveType.EMAIL in types


# ── Redaction leaves no trace ──────────────────────────────────────────


class TestRedactionSafety:
    """After redaction, none of the original sensitive values
    should appear in the output — even in partial form."""

    def test_email_fully_removed_after_redaction(self, detector):
        email = "private@secretdomain.co.uk"
        redacted = detector.redact(f"send to {email} for details")
        assert email not in redacted
        # The domain part alone should also not appear verbatim
        assert "secretdomain" not in redacted

    def test_redaction_marker_present_after_replacement(self, detector):
        redacted = detector.redact("reach me at user@example.com")
        assert "[EMAIL]" in redacted

    def test_multiple_redactions_do_not_overlap(self, detector):
        text = "a@a.com and b@b.com"
        redacted = detector.redact(text)
        # Both originals gone
        assert "a@a.com" not in redacted
        assert "b@b.com" not in redacted
        # Text structure preserved around them
        assert " and " in redacted

    def test_redact_password_value(self, detector):
        text = "password=supersecret123"
        redacted = detector.redact(text)
        assert "supersecret123" not in redacted


# ── Case-insensitive credential keyword detection ─────────────────────


class TestCaseInsensitiveDetection:
    """Credential keywords must be detected regardless of case."""

    @pytest.mark.parametrize("text", [
        "API_KEY=abc123",
        "Api_Key=abc123",
        "api_key=abc123",
        "APIKEY=abc123",
    ])
    def test_api_key_variants_detected(self, detector, text):
        assert detector.has_sensitive_data(text)

    @pytest.mark.parametrize("text", [
        "Password=hunter22",
        "PASSWORD=hunter22",
        "password=hunter22",
        "Passwd=hunter22",
        "pwd=hunter22",
    ])
    def test_password_variants_detected(self, detector, text):
        assert detector.has_sensitive_data(text)


# ── Private IP and localhost detection ────────────────────────────────


class TestPrivateNetworkDetection:
    """Private network addresses must be caught as sensitive."""

    @pytest.mark.parametrize("text", [
        "server at 192.168.1.100",
        "internal host 10.0.0.5",
        "staging at 172.16.0.1",
        "loopback 127.0.0.1",
        "local service at localhost:8080",
    ])
    def test_private_address_detected(self, detector, text):
        assert detector.has_sensitive_data(text), (
            f"Expected sensitive detection for: {text!r}"
        )


# ── Luhn-validated credit card strictness ─────────────────────────────


class TestCreditCardLuhnStrictness:
    """Only Luhn-valid card numbers should be flagged.
    Random digit strings of card-number length must not be false positives."""

    def test_valid_luhn_detected(self, detector):
        # 4532015112830366 passes Luhn
        assert SensitiveType.CREDIT_CARD in detector.get_sensitive_types(
            "card 4532015112830366 on file"
        )

    def test_invalid_luhn_not_detected_as_credit_card(self, detector):
        # 4532015112830367 fails Luhn (last digit off by 1)
        types = detector.get_sensitive_types("number 4532015112830367")
        assert SensitiveType.CREDIT_CARD not in types

    def test_invalid_digit_sequence_not_detected_as_credit_card(self, detector):
        # 1234 5678 9012 3456 fails Luhn — same card-like shape, must not match
        types = detector.get_sensitive_types("number 1234 5678 9012 3456")
        assert SensitiveType.CREDIT_CARD not in types


# ── Detector idempotency ──────────────────────────────────────────────


class TestDetectorIdempotency:
    """Running detect() twice on the same text must return the same result."""

    def test_detect_is_idempotent(self, detector):
        text = "email: user@example.com, api_key=abc123456"
        first = detector.detect(text)
        second = detector.detect(text)
        assert len(first) == len(second)
        for m1, m2 in zip(first, second):
            assert m1.sensitive_type == m2.sensitive_type
            assert m1.start == m2.start
            assert m1.end == m2.end

    def test_redact_is_idempotent_on_clean_text(self, detector):
        text = "Nothing sensitive here."
        assert detector.redact(text) == text
        assert detector.redact(detector.redact(text)) == text
