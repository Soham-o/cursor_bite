# Cursor Bite — Privacy Policies
# ============================================================
# Privacy policy definitions and evaluation.
#
# IMPORTANT: No user content (text, prompts, results) is logged.
# Only technical events are logged: policy decisions, reasons.

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from config.settings import settings
from infrastructure.privacy.detector import SensitiveMatch, sensitive_detector
from utils.logger import get_logger

logger = get_logger("infrastructure.privacy.policies")


# ── Policy Decision ────────────────────────────────────────────────

class PolicyDecision(str, Enum):
    """Result of evaluating privacy policies."""

    ALLOW_LOCAL = "allow_local"
    ALLOW_EXTERNAL_WITH_WARNING = "allow_external_with_warning"
    ALLOW_EXTERNAL = "allow_external"
    BLOCK = "block"


@dataclass
class PolicyEvaluation:
    """Result of a privacy policy evaluation."""

    decision: PolicyDecision
    reason: str = ""
    sensitive_matches: list[SensitiveMatch] = field(default_factory=list)
    requires_consent: bool = False
    consent_message: str = ""


# ── Privacy Policies ───────────────────────────────────────────────

class PrivacyPolicies:
    """Evaluates privacy policies against content before processing."""

    def evaluate(
        self,
        text: str,
        requires_external: bool = False,
        context: str = "",
    ) -> PolicyEvaluation:
        """Evaluate privacy policies for the given text.

        Args:
            text: The text/content to evaluate.
            requires_external: Whether the operation requires external processing.
            context: Description of what the text will be used for.

        Returns:
            PolicyEvaluation with the decision and any sensitive matches.
        """
        if not text:
            return PolicyEvaluation(
                decision=PolicyDecision.ALLOW_LOCAL,
                reason="No text to evaluate.",
            )

        # Check offline mode first
        if settings.privacy_offline_mode:
            if requires_external:
                return PolicyEvaluation(
                    decision=PolicyDecision.BLOCK,
                    reason="Offline mode is enabled. External processing is not allowed.",
                )
            return self._evaluate_local(text)

        # PRIVACY BOUNDARY: sensitivity policy only applies to processing
        # that would send data off the device. Local processing is never
        # blocked for containing sensitive data — the principle is
        # "sensitive data should not leave the device unintentionally",
        # not "sensitive data may not be touched at all". This early
        # return must stay ahead of the sensitive-data check below.
        if not requires_external:
            return self._evaluate_local(text)

        # From here on, requires_external is True.
        sensitive_matches = sensitive_detector.detect(text)

        if sensitive_matches:
            if settings.privacy_sensitive_data_protection:
                types = list(dict.fromkeys(m.sensitive_type.value for m in sensitive_matches))
                return PolicyEvaluation(
                    decision=PolicyDecision.BLOCK,
                    reason=(
                        f"Sensitive data detected: {', '.join(types)}. "
                        "The Privacy Gateway has blocked this operation to protect your data."
                    ),
                    sensitive_matches=sensitive_matches,
                )
            else:
                if settings.privacy_external_warning:
                    return PolicyEvaluation(
                        decision=PolicyDecision.ALLOW_EXTERNAL_WITH_WARNING,
                        reason="Sensitive data detected. External processing is allowed but not recommended.",
                        sensitive_matches=sensitive_matches,
                        requires_consent=True,
                        consent_message=(
                            "This text contains sensitive information. "
                            "Sending it to an external service may expose your data. Continue anyway?"
                        ),
                    )

        # No sensitive data (or fell through above with warnings disabled)
        # — evaluate the plain external-processing requirement.
        if settings.privacy_external_warning:
            return PolicyEvaluation(
                decision=PolicyDecision.ALLOW_EXTERNAL_WITH_WARNING,
                reason="This operation requires external processing.",
                requires_consent=True,
                consent_message=(
                    "This action will send data to an external service. Continue? "
                    "(Note: offline mode is off)"
                ),
            )
        return PolicyEvaluation(
            decision=PolicyDecision.ALLOW_EXTERNAL,
            reason="External processing allowed.",
        )

    def _evaluate_local(self, text: str) -> PolicyEvaluation:
        """Evaluate for local-only processing."""
        sensitive_matches = sensitive_detector.detect(text)

        if sensitive_matches and settings.privacy_sensitive_data_protection:
            logger.warning(
                "Sensitive data detected in local processing context. "
                f"Types: {', '.join(m.sensitive_type.value for m in sensitive_matches[:3])}"
            )

        return PolicyEvaluation(
            decision=PolicyDecision.ALLOW_LOCAL,
            reason="Local processing is allowed.",
            sensitive_matches=sensitive_matches if sensitive_matches else [],
        )

    # ── Check Retention Policies ─────────────────────────────────

    def should_retain_text(self) -> bool:
        """Whether captured text should be retained."""
        return not settings.privacy_no_data_retention

    def should_retain_screenshot(self) -> bool:
        """Whether screenshots should be saved."""
        return settings.privacy_screenshot_retention

    def should_protect_clipboard(self) -> bool:
        """Whether clipboard protection is enabled."""
        return settings.privacy_clipboard_protection

    # ── Summary ─────────────────────────────────────────────────

    def get_policy_summary(self) -> dict:
        """Get a summary of current privacy policy settings."""
        return {
            "offline_mode": settings.privacy_offline_mode,
            "no_data_retention": settings.privacy_no_data_retention,
            "clipboard_protection": settings.privacy_clipboard_protection,
            "screenshot_retention": settings.privacy_screenshot_retention,
            "sensitive_data_protection": settings.privacy_sensitive_data_protection,
            "external_processing_warning": settings.privacy_external_warning,
        }
