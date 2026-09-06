# Cursor Bite — Privacy Gateway Tests
# ============================================================
# Verifies the LOCAL / EXTERNAL / BLOCK decision logic in
# PrivacyPolicies and PrivacyGateway. `settings` is a module-level
# singleton, so each test resets it via the `clean_settings` fixture
# instead of relying on ordering.
#
# PRIVACY BOUNDARY UNDER TEST:
#   Sensitive data + LOCAL processing    -> ALLOW_LOCAL (never blocked)
#   Sensitive data + EXTERNAL processing -> BLOCK or consent, per policy
# The principle is "sensitive data should not leave the device
# unintentionally" — not "sensitive data may never be processed".

import pytest

from config.settings import settings
from domain.models import PrivacyDecision
from infrastructure.privacy.gateway import PrivacyGateway
from infrastructure.privacy.policies import PolicyDecision, PrivacyPolicies

SENSITIVE_TEXT = "email me at person@example.com"
CLEAN_TEXT = "Hello world"


@pytest.fixture()
def clean_settings():
    """Snapshot and restore settings._config around each test."""
    original = dict(settings._config)
    settings._config = {}
    yield settings
    settings._config = original


@pytest.fixture()
def policies() -> PrivacyPolicies:
    return PrivacyPolicies()


@pytest.fixture()
def gateway() -> PrivacyGateway:
    return PrivacyGateway()


# ── The seven required local-vs-external x sensitivity scenarios ──────

class TestPrivacyBoundaryMatrix:
    """1-7 from the correction-pass spec: local processing must never be
    blocked for sensitivity; external processing follows normal policy."""

    def test_1_clean_text_local_allows_local(self, clean_settings, policies):
        clean_settings.set("privacy.offline_mode", False)
        clean_settings.set("privacy.sensitive_data_protection", True)
        result = policies.evaluate(CLEAN_TEXT, requires_external=False)
        assert result.decision == PolicyDecision.ALLOW_LOCAL

    def test_2_sensitive_text_local_still_allows_local(self, clean_settings, policies):
        clean_settings.set("privacy.offline_mode", False)
        clean_settings.set("privacy.sensitive_data_protection", True)
        result = policies.evaluate(SENSITIVE_TEXT, requires_external=False)
        assert result.decision == PolicyDecision.ALLOW_LOCAL
        # sensitive matches are still surfaced for visibility, just not blocked
        assert result.sensitive_matches

    def test_3_clean_text_external_warning_disabled_allows_external(self, clean_settings, policies):
        clean_settings.set("privacy.offline_mode", False)
        clean_settings.set("privacy.external_processing_warning", False)
        result = policies.evaluate(CLEAN_TEXT, requires_external=True)
        assert result.decision == PolicyDecision.ALLOW_EXTERNAL
        assert not result.requires_consent

    def test_4_clean_text_external_warning_enabled_requires_consent(self, clean_settings, policies):
        clean_settings.set("privacy.offline_mode", False)
        clean_settings.set("privacy.external_processing_warning", True)
        result = policies.evaluate(CLEAN_TEXT, requires_external=True)
        assert result.decision == PolicyDecision.ALLOW_EXTERNAL_WITH_WARNING
        assert result.requires_consent

    def test_5_sensitive_text_external_protection_enabled_blocks(self, clean_settings, policies):
        clean_settings.set("privacy.offline_mode", False)
        clean_settings.set("privacy.sensitive_data_protection", True)
        result = policies.evaluate(SENSITIVE_TEXT, requires_external=True)
        assert result.decision == PolicyDecision.BLOCK
        assert result.sensitive_matches

    def test_6_offline_mode_local_allows_local(self, clean_settings, policies):
        clean_settings.set("privacy.offline_mode", True)
        result = policies.evaluate(CLEAN_TEXT, requires_external=False)
        assert result.decision == PolicyDecision.ALLOW_LOCAL

    def test_7_offline_mode_external_blocks(self, clean_settings, policies):
        clean_settings.set("privacy.offline_mode", True)
        result = policies.evaluate(CLEAN_TEXT, requires_external=True)
        assert result.decision == PolicyDecision.BLOCK

    def test_offline_mode_local_allows_even_with_sensitive_text(self, clean_settings, policies):
        # Offline mode's local path must also follow the "never block
        # local processing for sensitivity" rule.
        clean_settings.set("privacy.offline_mode", True)
        result = policies.evaluate(SENSITIVE_TEXT, requires_external=False)
        assert result.decision == PolicyDecision.ALLOW_LOCAL


class TestOfflineMode:
    def test_offline_mode_blocks_external_requirement(self, clean_settings, policies):
        clean_settings.set("privacy.offline_mode", True)
        result = policies.evaluate("Hello world", requires_external=True)
        assert result.decision == PolicyDecision.BLOCK

    def test_offline_mode_allows_local_processing(self, clean_settings, policies):
        clean_settings.set("privacy.offline_mode", True)
        result = policies.evaluate("Hello world", requires_external=False)
        assert result.decision == PolicyDecision.ALLOW_LOCAL


class TestSensitiveDataBlocking:
    def test_sensitive_data_blocks_only_when_external_and_protection_enabled(self, clean_settings, policies):
        # Corrected from the earlier version of this test, which asserted
        # BLOCK for requires_external=False — that encoded the bug fixed
        # in this pass. Local processing must not be blocked.
        clean_settings.set("privacy.offline_mode", False)
        clean_settings.set("privacy.sensitive_data_protection", True)
        result = policies.evaluate("email me at person@example.com", requires_external=True)
        assert result.decision == PolicyDecision.BLOCK
        assert result.sensitive_matches

    def test_sensitive_data_does_not_block_local_processing(self, clean_settings, policies):
        clean_settings.set("privacy.offline_mode", False)
        clean_settings.set("privacy.sensitive_data_protection", True)
        result = policies.evaluate("email me at person@example.com", requires_external=False)
        assert result.decision == PolicyDecision.ALLOW_LOCAL

    def test_sensitive_data_allowed_with_warning_when_protection_disabled(self, clean_settings, policies):
        clean_settings.set("privacy.offline_mode", False)
        clean_settings.set("privacy.sensitive_data_protection", False)
        clean_settings.set("privacy.external_processing_warning", True)
        result = policies.evaluate("email me at person@example.com", requires_external=True)
        assert result.decision == PolicyDecision.ALLOW_EXTERNAL_WITH_WARNING
        assert result.requires_consent

    def test_clean_text_not_blocked(self, clean_settings, policies):
        clean_settings.set("privacy.offline_mode", False)
        clean_settings.set("privacy.sensitive_data_protection", True)
        result = policies.evaluate("Hello world", requires_external=False)
        assert result.decision == PolicyDecision.ALLOW_LOCAL


class TestExternalProcessing:
    def test_external_without_warning_setting_allows_directly(self, clean_settings, policies):
        clean_settings.set("privacy.offline_mode", False)
        clean_settings.set("privacy.external_processing_warning", False)
        result = policies.evaluate("Hello world", requires_external=True)
        assert result.decision == PolicyDecision.ALLOW_EXTERNAL
        assert not result.requires_consent

    def test_external_with_warning_setting_requires_consent(self, clean_settings, policies):
        clean_settings.set("privacy.offline_mode", False)
        clean_settings.set("privacy.external_processing_warning", True)
        result = policies.evaluate("Hello world", requires_external=True)
        assert result.decision == PolicyDecision.ALLOW_EXTERNAL_WITH_WARNING
        assert result.requires_consent


class TestGatewayIntegration:
    def test_gateway_allows_sensitive_text_locally_end_to_end(self, clean_settings, gateway):
        # Corrected from the earlier version of this test, which used
        # requires_external=False and asserted is_blocked — that encoded
        # the bug fixed in this pass.
        clean_settings.set("privacy.offline_mode", False)
        clean_settings.set("privacy.sensitive_data_protection", True)
        result = gateway.evaluate("password=hunter22", action_name="explain", requires_external=False)
        assert result.is_allowed
        assert result.is_local_only
        assert result.text == "password=hunter22"

    def test_gateway_blocks_sensitive_text_when_external_end_to_end(self, clean_settings, gateway):
        clean_settings.set("privacy.offline_mode", False)
        clean_settings.set("privacy.sensitive_data_protection", True)
        result = gateway.evaluate("password=hunter22", action_name="search_web", requires_external=True)
        assert result.is_blocked
        assert result.text is None

    def test_gateway_allows_clean_text_end_to_end(self, clean_settings, gateway):
        clean_settings.set("privacy.offline_mode", False)
        clean_settings.set("privacy.sensitive_data_protection", True)
        result = gateway.evaluate("Hello world", action_name="explain", requires_external=False)
        assert result.is_allowed
        assert result.text == "Hello world"

    def test_gateway_is_blocked_convenience_method_checks_local_by_default(self, clean_settings, gateway):
        # is_blocked() evaluates with requires_external=False, so it
        # should never report sensitive-but-local text as blocked.
        clean_settings.set("privacy.offline_mode", False)
        clean_settings.set("privacy.sensitive_data_protection", True)
        assert gateway.is_blocked("api_key=abcd1234efgh5678") is False
        assert gateway.is_blocked("Hello world") is False

    def test_gateway_can_process_external_reports_sensitive_block(self, clean_settings, gateway):
        clean_settings.set("privacy.offline_mode", False)
        clean_settings.set("privacy.sensitive_data_protection", True)
        assert gateway.can_process_external("api_key=abcd1234efgh5678") is False
        assert gateway.can_process_external("Hello world") is True

    def test_gateway_redact_sensitive_uses_detector(self, clean_settings, gateway):
        redacted = gateway.redact_sensitive("contact person@example.com")
        assert "person@example.com" not in redacted


class TestCanProcessExternal:
    """can_process_external() must reflect a genuinely external-allowed
    decision only. Regression coverage for two bugs fixed in this pass:
    (1) it used to also return True for LOCAL_PROCESSING, which is not
    an external-processing decision at all; (2) ALLOW_EXTERNAL_WITH_WARNING
    used to collapse into the same PrivacyDecision as plain SAFE_EXTERNAL,
    losing the consent distinction at the decision-enum level."""

    def test_local_decision_is_not_externally_processable(self, clean_settings, gateway):
        clean_settings.set("privacy.offline_mode", False)
        result = gateway.evaluate(CLEAN_TEXT, requires_external=False)
        assert result.decision == PrivacyDecision.LOCAL_PROCESSING
        # The gate can_process_external() uses must exclude LOCAL_PROCESSING.
        assert result.decision not in (PrivacyDecision.SAFE_EXTERNAL, PrivacyDecision.WARN)

    def test_safe_external_decision_is_externally_processable(self, clean_settings, gateway):
        clean_settings.set("privacy.offline_mode", False)
        clean_settings.set("privacy.external_processing_warning", False)
        result = gateway.evaluate(CLEAN_TEXT, requires_external=True)
        assert result.decision == PrivacyDecision.SAFE_EXTERNAL
        assert gateway.can_process_external(CLEAN_TEXT) is True

    def test_warning_consent_decision_preserves_requires_consent(self, clean_settings, gateway):
        clean_settings.set("privacy.offline_mode", False)
        clean_settings.set("privacy.external_processing_warning", True)
        result = gateway.evaluate(CLEAN_TEXT, requires_external=True)
        # Distinct decision from plain SAFE_EXTERNAL — this is the fix.
        assert result.decision == PrivacyDecision.WARN
        assert result.decision != PrivacyDecision.SAFE_EXTERNAL
        assert result.requires_consent is True
        # WARN is still external-allowed, pending that consent.
        assert gateway.can_process_external(CLEAN_TEXT) is True

    def test_blocked_decision_is_not_externally_processable(self, clean_settings, gateway):
        clean_settings.set("privacy.offline_mode", False)
        clean_settings.set("privacy.sensitive_data_protection", True)
        result = gateway.evaluate(SENSITIVE_TEXT, requires_external=True)
        assert result.decision == PrivacyDecision.BLOCKED
        assert gateway.can_process_external(SENSITIVE_TEXT) is False


class TestNoUserContentInLogs:
    """The pipeline/gateway docstrings promise user content is never logged.
    We can't fully audit logging sinks here, but we can assert the gateway
    doesn't smuggle raw sensitive text into the `reason` string it returns
    (which does get logged by the gateway)."""

    def test_block_reason_does_not_contain_the_sensitive_value(self, clean_settings, gateway):
        clean_settings.set("privacy.offline_mode", False)
        clean_settings.set("privacy.sensitive_data_protection", True)
        secret_email = "topsecretperson@example.com"
        result = gateway.evaluate(f"contact {secret_email}", requires_external=True)
        assert result.is_blocked
        assert secret_email not in result.reason
