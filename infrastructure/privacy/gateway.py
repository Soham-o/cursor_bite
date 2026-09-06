# Cursor Bite — Privacy Gateway
# ============================================================
# The Privacy Gateway is the central decision point for all
# content processing in Cursor Bite.
#
# Architecture:
#   Input (text/content)
#       |
#       v
#   Context Processor
#       |
#       v
#   Privacy Gateway  <── Policy Engine + Sensitive Data Detector
#       |
#       ├── LOCAL PROCESSING  → process locally (OCR, Argos, Ollama)
#       ├── SAFE EXTERNAL     → process externally with consent
#       └── BLOCK / WARN      → protect user data
#
# IMPORTANT: No user content (text, prompts, results) is logged.
# Only technical events are logged: action names, decisions, reasons.

import logging
from typing import Optional

from config.settings import settings
from domain.models import PrivacyDecision, ProcessingResult
from infrastructure.privacy.detector import SensitiveMatch, sensitive_detector
from infrastructure.privacy.policies import (
    PolicyDecision as PolicyDecisionType,
    PolicyEvaluation,
    PrivacyPolicies,
)
from utils.logger import get_logger

logger = get_logger("infrastructure.privacy.gateway")


# ── Privacy Gateway ────────────────────────────────────────────────

class PrivacyGateway:
    """Central privacy decision engine for Cursor Bite.

    Every piece of content that enters Cursor Bite passes through
    this gateway before being processed.
    """

    def __init__(self) -> None:
        self._policies = PrivacyPolicies()

    # ── Primary Entry Point ─────────────────────────────────────

    def evaluate(
        self,
        text: str,
        action_name: str = "",
        requires_external: bool = False,
    ) -> "PrivacyEvaluationResult":
        """Evaluate content through the privacy gateway.

        Args:
            text: The text/content to evaluate.
            action_name: Name of the action being performed.
            requires_external: Whether the action needs external services.

        Returns:
            PrivacyEvaluationResult with the decision and any data.
        """
        context = f"action={action_name}" if action_name else "context=unknown"

        logger.debug(f"Privacy Gateway evaluating: {context}")

        # Run policy evaluation
        policy_result = self._policies.evaluate(text, requires_external, context)

        # Convert to our result type
        decision = self._map_policy_decision(policy_result.decision)

        # Log only technical info — no user content
        logger.info(
            f"Privacy Gateway decision: {decision.value} for {context}. "
            f"Reason: {policy_result.reason}"
        )

        return PrivacyEvaluationResult(
            decision=decision,
            text=text if decision != PrivacyDecision.BLOCKED else None,
            sensitive_matches=policy_result.sensitive_matches,
            reason=policy_result.reason,
            requires_consent=policy_result.requires_consent,
            consent_message=policy_result.consent_message,
        )

    # ── Convenience Methods ─────────────────────────────────────

    def can_process_locally(self, text: str, action_name: str = "") -> bool:
        """Quick check: can this text be processed locally?"""
        result = self.evaluate(text, action_name, requires_external=False)
        return result.decision == PrivacyDecision.LOCAL_PROCESSING

    def can_process_external(self, text: str, action_name: str = "") -> bool:
        """Quick check: can this text be processed externally?

        BUG FIXED: previously also returned True for LOCAL_PROCESSING,
        which is semantically wrong — a decision to process locally says
        nothing about whether external processing is permitted. Only
        genuinely external-allowed decisions (SAFE_EXTERNAL, or WARN
        which is external-allowed pending user consent) count here.
        Callers that also need to know about the consent requirement
        should check `result.requires_consent` via `evaluate()` directly.
        """
        result = self.evaluate(text, action_name, requires_external=True)
        return result.decision in (
            PrivacyDecision.SAFE_EXTERNAL,
            PrivacyDecision.WARN,
        )

    def is_blocked(self, text: str, action_name: str = "") -> bool:
        """Quick check: is this text blocked by privacy policies?"""
        result = self.evaluate(text, action_name, requires_external=False)
        return result.decision == PrivacyDecision.BLOCKED

    def redact_sensitive(self, text: str) -> str:
        """Redact sensitive data from text for safe display/logging."""
        return sensitive_detector.redact(text)

    # ── Policy Access ───────────────────────────────────────────

    @property
    def policies(self) -> PrivacyPolicies:
        return self._policies

    # ── Helpers ─────────────────────────────────────────────────

    def _map_policy_decision(self, policy_decision: PolicyDecisionType) -> PrivacyDecision:
        """Map PolicyDecision to PrivacyDecision.

        ALLOW_EXTERNAL_WITH_WARNING maps to its own PrivacyDecision.WARN
        value rather than collapsing into SAFE_EXTERNAL — a future UI
        needs to distinguish "safe to send externally" from "external,
        but must ask the user first" at the decision level, not just via
        the separate `requires_consent` flag on the result.
        """
        mapping = {
            PolicyDecisionType.ALLOW_LOCAL: PrivacyDecision.LOCAL_PROCESSING,
            PolicyDecisionType.ALLOW_EXTERNAL: PrivacyDecision.SAFE_EXTERNAL,
            PolicyDecisionType.ALLOW_EXTERNAL_WITH_WARNING: PrivacyDecision.WARN,
            PolicyDecisionType.BLOCK: PrivacyDecision.BLOCKED,
        }
        return mapping.get(policy_decision, PrivacyDecision.BLOCKED)


# ── Privacy Evaluation Result ──────────────────────────────────────

class PrivacyEvaluationResult:
    """Result of a privacy gateway evaluation."""

    def __init__(
        self,
        decision: PrivacyDecision,
        text: Optional[str] = None,
        sensitive_matches: list = None,
        reason: str = "",
        requires_consent: bool = False,
        consent_message: str = "",
    ) -> None:
        self.decision = decision
        self.text = text
        self.sensitive_matches = sensitive_matches or []
        self.reason = reason
        self.requires_consent = requires_consent
        self.consent_message = consent_message

    @property
    def is_allowed(self) -> bool:
        return self.decision != PrivacyDecision.BLOCKED

    @property
    def is_local_only(self) -> bool:
        return self.decision == PrivacyDecision.LOCAL_PROCESSING

    @property
    def is_blocked(self) -> bool:
        return self.decision == PrivacyDecision.BLOCKED

    def to_processing_result(self) -> ProcessingResult:
        """Convert to a ProcessingResult for pipeline compatibility."""
        if self.is_blocked:
            sensitive_types = list(dict.fromkeys(
                m.sensitive_type.value for m in self.sensitive_matches
            ))
            return ProcessingResult(
                success=False,
                error=self.reason or "Processing blocked by Privacy Gateway.",
                metadata={
                    "sensitive_types": sensitive_types,
                    "privacy_decision": self.decision.value,
                },
            )

        return ProcessingResult(
            success=True,
            data=self.text or "",
            metadata={
                "privacy_decision": self.decision.value,
                "sensitive_detected": len(self.sensitive_matches) > 0,
            },
        )


# ── Module-level instance ──────────────────────────────────────────

privacy_gateway = PrivacyGateway()
"""Global privacy gateway instance."""
