# Cursor Bite — Output Sanitizer and Contract Validator
# ============================================================
# Post-processing layer that enforces single-action contracts on AI output:
#   - Strips leading/trailing chat boilerplate ("Here is...", "Rewritten version:")
#   - Strips unrequested headings and artificial sections ("Key Insights", "Actionable Conclusions")
#   - Drops unrequested alternatives ("Alternatively:", "Option 2:")
#   - Validates contract compliance and provides single-shot correction prompts

from __future__ import annotations

import re
from typing import Optional, Tuple

from domain.models import ActionKind


# Leading conversational preambles to strip
_CHAT_PREAMBLE_PATTERNS = [
    r"^(?:Here\s+(?:is|are|'s)|Sure|Certainly|Below\s+is|Here\s+is\s+a)\s+[^:\n]*:\s*",
    r"^(?:Rewritten\s+version|Rewritten\s+text|Summary|In\s+summary|Clean\s+summary|Explanation)\s*:\s*",
    r"^(?:Here\s+is\s+your\s+rewritten\s+text|Here\s+is\s+the\s+rewritten\s+version|Here\s+is\s+a\s+summary\s+of\s+the\s+text)\s*:\s*",
    r"^(?:Here\s+are\s+the\s+key\s+points|Here\s+is\s+the\s+explanation)\s*:\s*",
]

# Patterns for forbidden analytical headings
_FORBIDDEN_SECTION_HEADER = re.compile(
    r"(?:^|\n)\s*(?:#+\s*|\*{1,2})?(?:Key\s+Insights|Actionable\s+Conclusions|Core\s+Thesis|Takeaways|Next\s+Steps|Analytical\s+Conclusions)(?:\*{1,2})?\s*:?",
    re.IGNORECASE,
)

# Patterns for alternative rewrite versions
_ALTERNATIVE_SPLIT = re.compile(
    r"\n\s*(?:Alternatively|Or,|Another\s+version|Option\s+\d|Version\s+\d|More\s+formal\s+version|More\s+concise\s+version)\s*:?",
    re.IGNORECASE,
)


class OutputSanitizer:
    """Sanitizes raw model output and enforces deterministic output contracts."""

    @classmethod
    def sanitize(
        cls,
        action: ActionKind,
        raw_text: str,
        original_input: Optional[str] = None,
    ) -> str:
        """Sanitize raw LLM output according to the action's contract."""
        if not raw_text or not raw_text.strip():
            return ""

        text = raw_text.strip()

        # 1. Strip code fence wrappers if the entire response is in a single code fence (e.g. ```text ... ```)
        fence_match = re.match(r"^```(?:[a-zA-Z0-9_-]+)?\s*\n([\s\S]*?)\n```$", text)
        if fence_match:
            text = fence_match.group(1).strip()

        # 2. Strip leading chat preambles
        for pat in _CHAT_PREAMBLE_PATTERNS:
            text = re.sub(pat, "", text, flags=re.IGNORECASE).strip()

        # 3. Action-specific sanitization
        if action == ActionKind.REWRITE:
            text = cls._sanitize_rewrite(text)
        elif action == ActionKind.SUMMARIZE:
            text = cls._sanitize_summarize(text)
        elif action == ActionKind.EXPLAIN:
            text = cls._sanitize_explain(text)
        elif action == ActionKind.TRANSLATE:
            text = cls._sanitize_translate(text)

        # 4. Strip surrounding quotation marks if they wrap the whole output
        if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
            if len(text) >= 2:
                inner = text[1:-1].strip()
                if inner:
                    text = inner

        return text.strip()

    @classmethod
    def _sanitize_rewrite(cls, text: str) -> str:
        """Enforce REWRITE contract: single output, zero alternatives, zero analytical sections."""
        # Drop everything after unrequested alternative offerings (e.g. "Alternatively, if you'd prefer...")
        split_alt = _ALTERNATIVE_SPLIT.split(text)
        if len(split_alt) > 1:
            text = split_alt[0].strip()

        # Drop everything after forbidden section headers (e.g. "Key Insights", "Actionable Conclusions")
        match_forbidden = _FORBIDDEN_SECTION_HEADER.search(text)
        if match_forbidden:
            text = text[: match_forbidden.start()].strip()

        # If a leading "**Summary**" or "**Rewritten:**" exists, remove that line
        text = re.sub(r"^\*{1,2}(?:Rewritten|Rewrite|Revised|Summary)\*{1,2}\s*:?\s*", "", text, flags=re.IGNORECASE)

        return text.strip()

    @classmethod
    def _sanitize_summarize(cls, text: str) -> str:
        """Enforce SUMMARIZE contract: clean summary, strip artificial section headers."""
        # If the output has "**Summary**\n... \n**Key Insights**\n...", extract the actual summary portion or clean up
        lines = text.splitlines()
        cleaned_lines = []

        for line in lines:
            line_str = line.strip()
            # If line is a forbidden heading like "**Key Insights**" or "**Actionable Conclusions**", drop it
            if re.match(r"^\*{0,2}#(?:#+)?\s*(?:Key\s+Insights|Actionable\s+Conclusions|Core\s+Thesis|Takeaways|Next\s+Steps)", line_str, re.I) or \
               re.match(r"^\*{1,2}(?:Key\s+Insights|Actionable\s+Conclusions|Core\s+Thesis|Takeaways|Next\s+Steps)\*{1,2}:?", line_str, re.I):
                continue

            # If line is just "**Summary**" or "**Summary:**", strip the heading itself
            if re.match(r"^\*{0,2}#+\s*Summary\b", line_str, re.I) or re.match(r"^\*{1,2}Summary\*{1,2}:?$", line_str, re.I):
                continue

            # Strip bold labels from bullet starts like "* **Core Thesis:** Harness..." -> "* Harness..."
            line_clean = re.sub(r"^(\s*[\*\-]\s*)\*\*(?:Core\s+Thesis|Key\s+Insight|Conclusion|Summary)\*\*:\s*", r"\1", line)
            cleaned_lines.append(line_clean)

        result = "\n".join(cleaned_lines).strip()
        return result if result else text.strip()

    @classmethod
    def _sanitize_explain(cls, text: str) -> str:
        """Enforce EXPLAIN contract: 2-4 sentences, no boilerplate."""
        # Strip leading section headers like "Overview:", "Definition:", "Concept:"
        text = re.sub(r"^(?:Overview|Definition|Concept|Explanation)\s*:\s*", "", text, flags=re.IGNORECASE)
        return text.strip()

    @classmethod
    def _sanitize_translate(cls, text: str) -> str:
        """Enforce TRANSLATE contract: pure translation only."""
        # Strip trailing notes (e.g. "Note: This is a formal translation...")
        text = re.split(r"\n\s*(?:Note|Notes|Translation\s+notes?)\s*:", text, flags=re.IGNORECASE)[0]
        return text.strip()

    @classmethod
    def is_contract_breached(cls, action: ActionKind, text: str) -> bool:
        """Check if output severely violates action contract even after initial sanitization."""
        if action == ActionKind.REWRITE:
            # Check for forbidden headings or multiple alternatives
            if _FORBIDDEN_SECTION_HEADER.search(text):
                return True
            if _ALTERNATIVE_SPLIT.search(text):
                return True
            # Rewrite should not look like a structured report with multiple markdown headers
            if len(re.findall(r"^#+\s+", text, re.MULTILINE)) >= 2:
                return True

        elif action == ActionKind.SUMMARIZE:
            if _FORBIDDEN_SECTION_HEADER.search(text):
                return True

        return False

    @classmethod
    def build_correction_prompt(cls, action: ActionKind, violated_output: str, original_input: str) -> Tuple[str, str]:
        """Build single-shot correction prompt if model violated the contract."""
        if action == ActionKind.REWRITE:
            system_prompt = (
                "You are a deterministic text rewriter. Output ONLY the raw rewritten text as a single clean paragraph.\n"
                "Do NOT include headings, sections ('Key Insights', 'Actionable Conclusions'), explanations, or alternatives."
            )
            user_prompt = (
                "Your previous response violated the contract by including unrequested sections or alternatives.\n"
                f"Original input:\n{original_input.strip()}\n\n"
                "Rewrite the text above as a SINGLE clean paragraph matching the input format. Output ONLY the rewritten text, nothing else."
            )
            return user_prompt, system_prompt

        elif action == ActionKind.SUMMARIZE:
            system_prompt = (
                "You are a deterministic summarizer. Output ONLY a concise summary paragraph.\n"
                "Do NOT include sections like 'Key Insights', 'Actionable Conclusions', or 'Summary'."
            )
            user_prompt = (
                "Your previous response violated the contract by including unrequested sections.\n"
                f"Original input:\n{original_input.strip()}\n\n"
                "Provide a single concise summary paragraph. Output ONLY the summary paragraph."
            )
            return user_prompt, system_prompt

        # Default fallback correction
        system_prompt = "Output the direct response only, with no headers or commentary."
        user_prompt = f"Original text:\n{original_input.strip()}\n\nRespond directly with no headers or commentary."
        return user_prompt, system_prompt
