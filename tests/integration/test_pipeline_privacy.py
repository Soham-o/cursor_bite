# Cursor Bite — Pipeline × Privacy Gateway Integration Tests
# ============================================================
# These tests exercise the full path from PrivacyPolicies through
# PrivacyGateway and into the objects that the Pipeline will call.
# They verify that the privacy boundary holds end-to-end without
# requiring any external services (translation, OCR, AI, search).

import pytest

from config.settings import settings
from domain.models import PrivacyDecision, ProcessingResult
from infrastructure.privacy.gateway import PrivacyGateway, PrivacyEvaluationResult
from infrastructure.privacy.policies import PolicyDecision, PrivacyPolicies


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture()
def clean_settings():
    """Snapshot and restore settings around each test."""
    original = dict(settings._config)
    settings._config = {}
    yield settings
    settings._config = original


@pytest.fixture()
def gateway() -> PrivacyGateway:
    return PrivacyGateway()


@pytest.fixture()
def policies() -> PrivacyPolicies:
    return PrivacyPolicies()


# ── PrivacyEvaluationResult → ProcessingResult conversion ─────────────


class TestEvaluationResultToProcessingResult:
    """to_processing_result() must produce a coherent ProcessingResult."""

    def test_blocked_result_is_failure(self, clean_settings, gateway):
        clean_settings.set("privacy.offline_mode", False)
        clean_settings.set("privacy.sensitive_data_protection", True)
        result = gateway.evaluate(
            "password=hunter22", action_name="search_web", requires_external=True
        )
        assert result.is_blocked
        pr: ProcessingResult = result.to_processing_result()
        assert pr.success is False
        assert pr.error

    def test_allowed_result_is_success(self, clean_settings, gateway):
        clean_settings.set("privacy.offline_mode", False)
        result = gateway.evaluate(
            "Hello world", action_name="explain", requires_external=False
        )
        assert result.is_allowed
        pr: ProcessingResult = result.to_processing_result()
        assert pr.success is True
        assert pr.data == "Hello world"

    def test_blocked_result_exposes_sensitive_types(self, clean_settings, gateway):
        clean_settings.set("privacy.offline_mode", False)
        clean_settings.set("privacy.sensitive_data_protection", True)
        result = gateway.evaluate(
            "email me at person@example.com", action_name="search_web", requires_external=True
        )
        assert result.is_blocked
        pr = result.to_processing_result()
        assert "sensitive_types" in pr.metadata
        assert "email" in pr.metadata["sensitive_types"]

    def test_allowed_result_includes_privacy_decision_in_metadata(self, clean_settings, gateway):
        clean_settings.set("privacy.offline_mode", False)
        result = gateway.evaluate("Hello world", action_name="explain", requires_external=False)
        pr = result.to_processing_result()
        assert "privacy_decision" in pr.metadata


# ── Policy × Gateway agreement ────────────────────────────────────────


class TestPoliciesAndGatewayAgree:
    """PolicyDecision and the PrivacyDecision emitted by the gateway must match."""

    def test_allow_local_maps_to_local_processing(self, clean_settings, policies, gateway):
        clean_settings.set("privacy.offline_mode", False)
        pol = policies.evaluate("Hello world", requires_external=False)
        gat = gateway.evaluate("Hello world", requires_external=False)
        assert pol.decision == PolicyDecision.ALLOW_LOCAL
        assert gat.decision == PrivacyDecision.LOCAL_PROCESSING

    def test_allow_external_maps_to_safe_external(self, clean_settings, policies, gateway):
        clean_settings.set("privacy.offline_mode", False)
        clean_settings.set("privacy.external_processing_warning", False)
        pol = policies.evaluate("Hello world", requires_external=True)
        gat = gateway.evaluate("Hello world", requires_external=True)
        assert pol.decision == PolicyDecision.ALLOW_EXTERNAL
        assert gat.decision == PrivacyDecision.SAFE_EXTERNAL

    def test_block_maps_to_blocked(self, clean_settings, policies, gateway):
        clean_settings.set("privacy.offline_mode", False)
        clean_settings.set("privacy.sensitive_data_protection", True)
        pol = policies.evaluate(
            "api_key=abcd1234efgh5678", requires_external=True
        )
        gat = gateway.evaluate(
            "api_key=abcd1234efgh5678", requires_external=True
        )
        assert pol.decision == PolicyDecision.BLOCK
        assert gat.decision == PrivacyDecision.BLOCKED

    def test_warn_maps_to_warn(self, clean_settings, policies, gateway):
        clean_settings.set("privacy.offline_mode", False)
        clean_settings.set("privacy.external_processing_warning", True)
        pol = policies.evaluate("Hello world", requires_external=True)
        gat = gateway.evaluate("Hello world", requires_external=True)
        assert pol.decision == PolicyDecision.ALLOW_EXTERNAL_WITH_WARNING
        assert gat.decision == PrivacyDecision.WARN


# ── Offline mode end-to-end ───────────────────────────────────────────


class TestOfflineModeEndToEnd:
    """Offline mode must block every external request, even for clean text."""

    def test_offline_blocks_all_external_regardless_of_text(self, clean_settings, gateway):
        clean_settings.set("privacy.offline_mode", True)
        for text in ["Hello world", "person@example.com", "password=hunter22"]:
            result = gateway.evaluate(text, requires_external=True)
            assert result.is_blocked, f"Expected block for: {text!r}"

    def test_offline_allows_all_local_regardless_of_text(self, clean_settings, gateway):
        clean_settings.set("privacy.offline_mode", True)
        for text in ["Hello world", "person@example.com", "password=hunter22"]:
            result = gateway.evaluate(text, requires_external=False)
            assert result.is_allowed, f"Expected allow for: {text!r}"


# ── Retention and clipboard policy helpers ─────────────────────────────


class TestRetentionPolicies:
    """Policy helper methods must reflect the current settings."""

    def test_should_retain_text_respects_no_data_retention_setting(self, clean_settings, policies):
        clean_settings.set("privacy.no_data_retention", True)
        assert policies.should_retain_text() is False

        clean_settings.set("privacy.no_data_retention", False)
        assert policies.should_retain_text() is True

    def test_should_protect_clipboard_respects_setting(self, clean_settings, policies):
        clean_settings.set("privacy.clipboard_protection", True)
        assert policies.should_protect_clipboard() is True

        clean_settings.set("privacy.clipboard_protection", False)
        assert policies.should_protect_clipboard() is False

    def test_should_retain_screenshot_respects_setting(self, clean_settings, policies):
        clean_settings.set("privacy.screenshot_retention", False)
        assert policies.should_retain_screenshot() is False

        clean_settings.set("privacy.screenshot_retention", True)
        assert policies.should_retain_screenshot() is True


# ── Policy summary ─────────────────────────────────────────────────────


class TestPolicySummary:
    """get_policy_summary() must include all expected keys."""

    EXPECTED_KEYS = {
        "offline_mode",
        "no_data_retention",
        "clipboard_protection",
        "screenshot_retention",
        "sensitive_data_protection",
        "external_processing_warning",
    }

    def test_policy_summary_contains_all_keys(self, clean_settings, policies):
        summary = policies.get_policy_summary()
        assert self.EXPECTED_KEYS <= set(summary.keys())

    def test_policy_summary_reflects_settings(self, clean_settings, policies):
        clean_settings.set("privacy.offline_mode", True)
        clean_settings.set("privacy.no_data_retention", True)
        summary = policies.get_policy_summary()
        assert summary["offline_mode"] is True
        assert summary["no_data_retention"] is True
