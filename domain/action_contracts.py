# Cursor Bite — Deterministic Action Contracts
# ============================================================
# Strict prompt generators enforcing single-action contracts:
# Each Cursor Bite action has ONE job. The model must behave like
# a deterministic tool, never a generic conversational chatbot.

from __future__ import annotations

import re
from typing import Optional, Tuple

from domain.models import ActionKind, ContextAnalysis, ContentDomain, ContentType


class ActionContracts:
    """Generates prompt pairs (user_prompt, system_prompt) adhering to strict single-action contracts."""

    @staticmethod
    def _detect_input_format(text: str) -> str:
        """Infer the structural format of the input text."""
        clean = text.strip()
        lines = [line.strip() for line in clean.splitlines() if line.strip()]

        if not lines:
            return "empty"

        is_bullet_list = all(
            re.match(r"^(\*|-|\+|\d+\.)\s+", line) for line in lines
        ) and len(lines) >= 2

        if is_bullet_list:
            return "bullet_list"

        if len(lines) == 1:
            words = clean.split()
            if len(words) <= 25 and clean.endswith((".", "!", "?")):
                return "single_sentence"
            return "single_paragraph"

        if len(lines) <= 4 and len(clean.split()) < 100:
            return "single_paragraph"

        return "multi_paragraph"

    @classmethod
    def build_rewrite_contract(
        cls,
        text: str,
        analysis: Optional[ContextAnalysis] = None,
    ) -> Tuple[str, str]:
        """Contract for REWRITE:
        ONE JOB: Rewrite the selected text for clarity, flow, and grammar.
        FORBIDDEN:
        - Chat filler ("Here is...", "Sure!")
        - Analytical headings ("Summary", "Key Insights", "Actionable Conclusions")
        - Answering questions or inventing new facts
        - Explaining changes or offering multiple alternatives
        MUST: Match input structure (sentence -> sentence, paragraph -> paragraph, list -> list).
        """
        input_fmt = cls._detect_input_format(text)
        domain_str = analysis.domain.value.replace("_", " ").title() if analysis else "General"

        format_rule = "Output a SINGLE rewritten paragraph."
        if input_fmt == "single_sentence":
            format_rule = "Output a SINGLE rewritten sentence."
        elif input_fmt == "bullet_list":
            format_rule = "Output a rewritten bullet list with the same number of items."

        system_prompt = (
            f"You are a deterministic text rewriting engine operating on {domain_str} text.\n"
            "CONTRACT RULES:\n"
            "1. Output ONLY the raw rewritten text. Zero chat filler, zero preamble, zero postscript.\n"
            f"2. {format_rule}\n"
            "3. Strictly preserve all facts, technical terms, names, and numbers without alteration.\n"
            "4. NEVER generate headings or report sections (strictly FORBIDDEN: 'Summary', 'Key Insights', 'Actionable Conclusions', 'Takeaways', 'Next Steps').\n"
            "5. NEVER provide alternatives (e.g. 'Alternatively:', 'Or:'). Provide exactly ONE high-quality version."
        )

        user_prompt = (
            f"ACTION: REWRITE\n"
            f"DOMAIN CONTEXT: {domain_str}\n"
            f"INPUT FORMAT: {input_fmt}\n"
            f"INPUT TEXT:\n{text.strip()}\n\n"
            f"OUTPUT CONTRACT: {format_rule} Reply with ONLY the rewritten text, nothing else."
        )

        return user_prompt, system_prompt

    @classmethod
    def build_summarize_contract(
        cls,
        text: str,
        analysis: Optional[ContextAnalysis] = None,
    ) -> Tuple[str, str]:
        """Contract for SUMMARIZE:
        ONE JOB: Produce a concise, dense summary of the input.
        FORBIDDEN:
        - Artificial sections ('Summary', 'Key Insights', 'Actionable Conclusions', 'Takeaways')
        - Conversational filler ('Here is a summary of the text:')
        - Speculating beyond the provided text
        MUST:
        - Output a single concise summary paragraph OR 3-5 concise bullets.
        """
        domain_str = analysis.domain.value.replace("_", " ").title() if analysis else "General"
        word_count = len(text.strip().split())

        # Decide whether to output a concise paragraph or bullet points based on length
        wants_bullets = word_count >= 140 or "\n-" in text or "\n*" in text

        if wants_bullets:
            format_instruction = (
                "Output 3 to 5 concise bullet points capturing the core facts.\n"
                "Do NOT use subheadings or category labels. Start directly with the bullet points."
            )
        else:
            format_instruction = (
                "Output a SINGLE clean, information-dense summary paragraph (2 to 4 sentences).\n"
                "Do NOT use bullet points, bold section names, or category labels."
            )

        system_prompt = (
            f"You are a deterministic summarization engine operating on {domain_str} text.\n"
            "CONTRACT RULES:\n"
            "1. Output ONLY the summary content. Zero conversational preamble, zero concluding remarks.\n"
            f"2. {format_instruction}\n"
            "3. STRICTLY FORBIDDEN: Do not create sections or headings like 'Summary', 'Key Insights', 'Actionable Conclusions', 'Core Thesis', or 'Next Steps'.\n"
            "4. Ground all claims strictly in the input text. Never invent details or outside facts."
        )

        user_prompt = (
            f"ACTION: SUMMARIZE\n"
            f"DOMAIN CONTEXT: {domain_str}\n"
            f"INPUT TEXT:\n{text.strip()}\n\n"
            f"OUTPUT CONTRACT:\n{format_instruction}\nReply with the summary ONLY."
        )

        return user_prompt, system_prompt

    @classmethod
    def build_explain_contract(
        cls,
        text: str,
        analysis: Optional[ContextAnalysis] = None,
    ) -> Tuple[str, str]:
        """Contract for EXPLAIN:
        ONE JOB: Explain the selected concept, term, or passage clearly and simply.
        FORBIDDEN:
        - Multi-page essays or generic encyclopedic definitions
        - Conversational greetings or sign-offs
        - Unsolicited headings or bullet-point breakdowns unless necessary
        MUST:
        - 2 to 4 sentences maximum in plain language.
        """
        domain_str = analysis.domain.value.replace("_", " ").title() if analysis else "General"
        grounding = ""
        if analysis and analysis.grounded_meaning:
            grounding = f" (specifically: {analysis.grounded_meaning})"

        system_prompt = (
            f"You are a precision concept explainer specializing in {domain_str}.\n"
            "CONTRACT RULES:\n"
            "1. Explain the text clearly and concisely in 2 to 4 sentences maximum.\n"
            "2. Explain WHAT it means and its core purpose or function in plain, practical language.\n"
            "3. Output ONLY the explanation. Zero greetings, zero sign-offs, zero meta-commentary.\n"
            "4. Do NOT output section headers (no 'Definition:', 'Overview:', etc.)."
        )

        user_prompt = (
            f"ACTION: EXPLAIN\n"
            f"DOMAIN CONTEXT: {domain_str}{grounding}\n"
            f"INPUT TEXT:\n{text.strip()}\n\n"
            "OUTPUT CONTRACT: 2 to 4 sentences explaining the concept. Output ONLY the explanation."
        )

        return user_prompt, system_prompt

    @classmethod
    def build_ask_contract(
        cls,
        text: str,
        question: str,
        analysis: Optional[ContextAnalysis] = None,
    ) -> Tuple[str, str]:
        """Contract for ASK AI:
        ONE JOB: Answer the user's specific question using the text as reference context.
        """
        domain_str = analysis.domain.value.replace("_", " ").title() if analysis else "General"

        system_prompt = (
            f"You are a focused contextual AI assistant in {domain_str}.\n"
            "CONTRACT RULES:\n"
            "1. Answer the question directly and concisely.\n"
            "2. Base the answer on the provided reference context if relevant.\n"
            "3. If the context does not contain the answer, answer succinctly from general knowledge or state so clearly.\n"
            "4. Be direct, factual, and avoid unnecessary preamble."
        )

        if text and text.strip():
            user_prompt = (
                f"REFERENCE CONTEXT ({domain_str}):\n{text.strip()}\n\n"
                f"QUESTION: {question.strip()}\n\n"
                "Answer directly:"
            )
        else:
            user_prompt = f"QUESTION: {question.strip()}\n\nAnswer directly:"

        return user_prompt, system_prompt

    @classmethod
    def build_translate_contract(
        cls,
        text: str,
        target_lang: str = "en",
        target_lang_name: str = "English",
    ) -> Tuple[str, str]:
        """Contract for TRANSLATE (used when offline Argos is unavailable or AI fallback is needed):
        ONE JOB: Translate the text into the target language.
        FORBIDDEN: Pronunciation notes, glossaries, explanations, commentary.
        """
        system_prompt = (
            f"You are a deterministic translation engine targeting {target_lang_name} ({target_lang}).\n"
            "CONTRACT RULES:\n"
            f"1. Translate the input text accurately into {target_lang_name}.\n"
            "2. Output ONLY the raw translated text.\n"
            "3. Preserve punctuation, formatting, and casing.\n"
            "4. NEVER include notes, glossaries, phonetic transcriptions, or commentary."
        )

        user_prompt = (
            f"ACTION: TRANSLATE to {target_lang_name}\n"
            f"INPUT TEXT:\n{text.strip()}\n\n"
            "OUTPUT CONTRACT: Raw translation ONLY."
        )

        return user_prompt, system_prompt
