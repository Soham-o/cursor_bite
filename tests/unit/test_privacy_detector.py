# Cursor Bite — Privacy Detector Tests
# ============================================================
# Verifies detection AND redaction behavior of SensitiveDataDetector.
# These tests never print/log the sensitive fixture values themselves;
# they only assert on match presence/type/count.

import pytest

from infrastructure.privacy.detector import SensitiveDataDetector, SensitiveType


@pytest.fixture()
def detector() -> SensitiveDataDetector:
    # Fresh instance per test — the module-level singleton is fine to use
    # in the app, but tests should not depend on shared mutable state.
    return SensitiveDataDetector()


# ── Credential-style patterns (KEY=VALUE / KEY: VALUE) ───────────────

class TestCredentialPatterns:
    @pytest.mark.parametrize("text", [
        "API_KEY=abc123",
        "API_KEY: abc123",
        "api_key=abcdef123456",
    ])
    def test_api_key_detected(self, detector, text):
        assert detector.has_sensitive_data(text)
        types = detector.get_sensitive_types(text)
        assert SensitiveType.API_KEY in types

    @pytest.mark.parametrize("text", [
        "password=secret",
        "password: hunter2",
        "pwd=letmein1",
    ])
    def test_password_detected(self, detector, text):
        assert detector.has_sensitive_data(text)
        types = detector.get_sensitive_types(text)
        assert SensitiveType.PASSWORD in types

    @pytest.mark.parametrize("text", [
        "token=abcdef",
        "my_token=abcdefghij1234567890",
        "auth_token=abcdefghij1234567890",
    ])
    def test_token_detected(self, detector, text):
        assert detector.has_sensitive_data(text)
        types = detector.get_sensitive_types(text)
        assert types  # some sensitive type should fire
        assert SensitiveType.UNKNOWN not in types


# ── Known secret formats ──────────────────────────────────────────────

class TestSecretFormats:
    def test_aws_access_key_detected(self, detector):
        text = "key is AKIAIOSFODNN7EXAMPLE in the config"
        assert detector.has_sensitive_data(text)
        assert SensitiveType.AWS_KEY in detector.get_sensitive_types(text)

    def test_github_token_detected(self, detector):
        text = "ghp_" + "a" * 36
        assert detector.has_sensitive_data(text)
        assert SensitiveType.GITHUB_TOKEN in detector.get_sensitive_types(text)

    def test_generic_high_entropy_credential_pair_detected(self, detector):
        # variable = long secret-looking value, single '=' or ':'
        text = "OPENAI_KEY=sk-" + "a" * 40
        assert detector.has_sensitive_data(text)


# ── Credit cards (Luhn-validated) ─────────────────────────────────────

class TestCreditCards:
    def test_valid_luhn_number_detected(self, detector):
        # 4532015112830366 passes Luhn
        text = "card number 4532015112830366 on file"
        assert detector.has_sensitive_data(text)
        assert SensitiveType.CREDIT_CARD in detector.get_sensitive_types(text)

    def test_invalid_luhn_number_not_flagged_as_credit_card(self, detector):
        # 4532015112830367 fails Luhn — same shape, should NOT match as a card
        text = "card number 4532015112830367 on file"
        types = detector.get_sensitive_types(text)
        assert SensitiveType.CREDIT_CARD not in types


# ── Normal content should NOT trigger false positives ─────────────────

class TestNoFalsePositives:
    @pytest.mark.parametrize("text", [
        "Hello world",
        "def foo(x, y):\n    return x + y",
        "Check this out: https://example.com/page?id=42",
        "The meeting is at 10:00 tomorrow.",
        "Please review chapter 3, section 2.1 of the report.",
    ])
    def test_normal_text_has_no_matches(self, detector, text):
        assert detector.detect(text) == []


# ── Redaction ───────────────────────────────────────────────────────

class TestRedaction:
    def test_redact_removes_sensitive_value(self, detector):
        text = "contact me at person@example.com for details"
        redacted = detector.redact(text)
        assert "person@example.com" not in redacted
        assert "[EMAIL]" in redacted

    def test_redact_preserves_surrounding_text(self, detector):
        text = "email person@example.com now"
        redacted = detector.redact(text)
        assert redacted.startswith("email ")
        assert redacted.endswith(" now")

    def test_redact_no_op_on_clean_text(self, detector):
        text = "Hello world"
        assert detector.redact(text) == text

    def test_redact_handles_multiple_matches(self, detector):
        text = "a@example.com and b@example.com"
        redacted = detector.redact(text)
        assert "a@example.com" not in redacted
        assert "b@example.com" not in redacted
