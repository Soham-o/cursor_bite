# Tests for ActionContracts and OutputSanitizer
# ============================================================

import pytest
from domain.action_contracts import ActionContracts
from domain.output_sanitizer import OutputSanitizer
from domain.models import ActionKind, ContextAnalysis, ContentDomain


class TestActionContracts:
    def test_rewrite_contract_negative_constraints(self):
        text = "Harness Engineering focuses on building resilient test harnesses."
        user_p, sys_p = ActionContracts.build_rewrite_contract(text)

        assert "Output ONLY the raw rewritten text" in sys_p
        assert "strictly FORBIDDEN: 'Summary', 'Key Insights'" in sys_p
        assert "NEVER provide alternatives" in sys_p
        assert "ACTION: REWRITE" in user_p
        assert text in user_p

    def test_summarize_contract_negative_constraints(self):
        text = "A short paragraph about software engineering."
        user_p, sys_p = ActionContracts.build_summarize_contract(text)

        assert "STRICTLY FORBIDDEN" in sys_p
        assert "Key Insights" in sys_p
        assert "Actionable Conclusions" in sys_p
        assert "ACTION: SUMMARIZE" in user_p

    def test_explain_contract(self):
        text = "RAG"
        analysis = ContextAnalysis(domain=ContentDomain.SOFTWARE_TECH, grounded_meaning="Retrieval-Augmented Generation")
        user_p, sys_p = ActionContracts.build_explain_contract(text, analysis)

        assert "2 to 4 sentences maximum" in sys_p
        assert "Retrieval-Augmented Generation" in user_p
        assert "ACTION: EXPLAIN" in user_p

    def test_ask_contract(self):
        text = "Context about models."
        user_p, sys_p = ActionContracts.build_ask_contract(text, "What is this?")

        assert "REFERENCE CONTEXT" in user_p
        assert "QUESTION: What is this?" in user_p


class TestOutputSanitizer:
    def test_strip_chat_preamble(self):
        raw = "Here is the rewritten version:\nHarness Engineering builds resilient test harnesses."
        sanitized = OutputSanitizer.sanitize(ActionKind.REWRITE, raw)
        assert sanitized == "Harness Engineering builds resilient test harnesses."

    def test_strip_rewrite_alternatives(self):
        raw = (
            "Harness Engineering builds resilient test harnesses.\n\n"
            "Alternatively, if you'd prefer a more concise version:\n"
            "Harness Engineering builds test harnesses."
        )
        sanitized = OutputSanitizer.sanitize(ActionKind.REWRITE, raw)
        assert sanitized == "Harness Engineering builds resilient test harnesses."

    def test_strip_forbidden_headings_in_rewrite(self):
        raw = (
            "Harness Engineering centers on robust test harnesses.\n\n"
            "**Key Insights**\n"
            "* Resilient test harnesses are essential.\n\n"
            "**Actionable Conclusions**\n"
            "* Deploy continuous validation."
        )
        sanitized = OutputSanitizer.sanitize(ActionKind.REWRITE, raw)
        assert sanitized == "Harness Engineering centers on robust test harnesses."
        assert "Key Insights" not in sanitized
        assert "Actionable Conclusions" not in sanitized

    def test_strip_forbidden_headings_in_summarize(self):
        raw = (
            "**Summary**\n"
            "Harness Engineering builds robust testing solutions.\n\n"
            "**Key Insights**\n"
            "* Continuous validation.\n"
            "* Standardized observability.\n\n"
            "**Actionable Conclusions**\n"
            "* Implement test harnesses."
        )
        sanitized = OutputSanitizer.sanitize(ActionKind.SUMMARIZE, raw)
        assert "Summary" not in sanitized
        assert "Key Insights" not in sanitized
        assert "Actionable Conclusions" not in sanitized
        assert "Harness Engineering builds robust testing solutions." in sanitized

    def test_contract_breach_detection(self):
        clean_text = "Clean rewritten paragraph without any extra sections."
        dirty_text = "Rewritten paragraph.\n\n**Key Insights**\n* Insight 1"

        assert not OutputSanitizer.is_contract_breached(ActionKind.REWRITE, clean_text)
        assert OutputSanitizer.is_contract_breached(ActionKind.REWRITE, dirty_text)
