# Cursor Bite — Context Intelligence Analyzer
# ============================================================
# Lightweight, deterministic context analysis layer.
#
# Analyzes selected text to infer:
#   1. Language & Script
#   2. Domain (Software/Tech, Finance, Legal, Science, General)
#   3. Content Type (Code, Error Log, Acronym, Prose, etc.)
#   4. User Intent (Explain, Debug, Expand, Summarize, Rewrite)
#   5. Confidence & Grounded Acronym Meanings
#   6. Adaptive Action Ranking
#
# IMPORTANT: This runs locally in microseconds with zero network calls,
# zero model inference, and no external vector databases.

from __future__ import annotations

import re
from typing import Optional

from domain.models import (
    ActionKind,
    ContentDomain,
    ContentType,
    ContextAnalysis,
    UserIntent,
)


# ── Grounded Acronym Knowledge ─────────────────────────────────────
# Prevents generic dictionary hallucinations for well-known technical terms.

GROUNDED_ACRONYMS: dict[str, tuple[str, ContentDomain]] = {
    "RAG": ("Retrieval-Augmented Generation (AI / LLMs)", ContentDomain.SOFTWARE_TECH),
    "LLM": ("Large Language Model (AI / Deep Learning)", ContentDomain.SOFTWARE_TECH),
    "AST": ("Abstract Syntax Tree (Compilers / Parsing)", ContentDomain.SOFTWARE_TECH),
    "DOM": ("Document Object Model (Web / Browser)", ContentDomain.SOFTWARE_TECH),
    "CRUD": ("Create, Read, Update, Delete (Database / APIs)", ContentDomain.SOFTWARE_TECH),
    "JWT": ("JSON Web Token (Authentication & Security)", ContentDomain.SOFTWARE_TECH),
    "REST": ("Representational State Transfer (Web Services)", ContentDomain.SOFTWARE_TECH),
    "CI/CD": ("Continuous Integration / Continuous Deployment (DevOps)", ContentDomain.SOFTWARE_TECH),
    "API": ("Application Programming Interface", ContentDomain.SOFTWARE_TECH),
    "SDK": ("Software Development Kit", ContentDomain.SOFTWARE_TECH),
    "HWND": ("Handle to a Window (Win32 OS Architecture)", ContentDomain.SOFTWARE_TECH),
    "UAC": ("User Account Control (Windows Security)", ContentDomain.SOFTWARE_TECH),
    "DPI": ("Dots Per Inch / Display Scaling", ContentDomain.SOFTWARE_TECH),
    "ORM": ("Object-Relational Mapping (Databases)", ContentDomain.SOFTWARE_TECH),
    "RPC": ("Remote Procedure Call (Distributed Systems)", ContentDomain.SOFTWARE_TECH),
    "SQL": ("Structured Query Language (Databases)", ContentDomain.SOFTWARE_TECH),
    "CSS": ("Cascading Style Sheets (Web Styling)", ContentDomain.SOFTWARE_TECH),
    "HTML": ("HyperText Markup Language (Web Structure)", ContentDomain.SOFTWARE_TECH),
    "JSON": ("JavaScript Object Notation (Data Interchange)", ContentDomain.SOFTWARE_TECH),
    "YAML": ("YAML Ain't Markup Language (Configuration)", ContentDomain.SOFTWARE_TECH),
    "NLP": ("Natural Language Processing (AI)", ContentDomain.SOFTWARE_TECH),
    "GPU": ("Graphics Processing Unit (Hardware / Compute)", ContentDomain.SOFTWARE_TECH),
    "TPU": ("Tensor Processing Unit (AI Hardware)", ContentDomain.SOFTWARE_TECH),
    "VRAM": ("Video Random Access Memory", ContentDomain.SOFTWARE_TECH),
    "ROI": ("Return on Investment (Finance / Business)", ContentDomain.BUSINESS_FINANCE),
    "EBITDA": ("Earnings Before Interest, Taxes, Depreciation, Amortization", ContentDomain.BUSINESS_FINANCE),
    "KPI": ("Key Performance Indicator (Business / Management)", ContentDomain.BUSINESS_FINANCE),
    "GDPR": ("General Data Protection Regulation (Privacy & Legal)", ContentDomain.LEGAL_COMPLIANCE),
    "TOS": ("Terms of Service (Legal Agreements)", ContentDomain.LEGAL_COMPLIANCE),
    "NDA": ("Non-Disclosure Agreement (Legal Contracts)", ContentDomain.LEGAL_COMPLIANCE),
}


# ── Lexical Indicators ─────────────────────────────────────────────

_CODE_PATTERNS = [
    r"\bdef\s+\w+\s*\(",
    r"\bclass\s+\w+",
    r"\bfunction\s+\w*\s*\(",
    r"\bimport\s+[\w\.]+",
    r"\bfrom\s+[\w\.]+\s+import\b",
    r"\b(const|let|var)\s+\w+\s*=",
    r"\breturn\s+[^;]+[;\n]",
    r"\bpublic\s+(static\s+)?\w+",
    r"\b(console\.log|print|printf)\s*\(",
    r"=>|\->",
    r"[{};]\s*$",
    r"\b(SELECT|FROM|WHERE|INSERT|UPDATE|DELETE)\b.*\b(FROM|INTO|TABLE|SET)\b",
]

_ERROR_PATTERNS = [
    r"Traceback \(most recent call last\):",
    r"\b(Error|Exception|Fault|Panic):\s",
    r"\bat\s+[\w\.<>]+\s*\([^)]+:\d+:\d+\)",
    r"\b(SyntaxError|TypeError|ValueError|KeyError|IndexError|AttributeError|NameError)\b",
    r"\bNullPointerException|Segmentation fault|Access violation\b",
    r"\bfailed with exit code \d+\b",
    r"\bHTTP (400|401|403|404|500|502|503)\b",
]

_TECH_KEYWORDS = {
    "asyncio", "python", "javascript", "typescript", "rust", "golang", "c++", "c#",
    "docker", "kubernetes", "git", "github", "linux", "windows", "macos", "kernel",
    "compiler", "thread", "mutex", "coroutine", "process", "memory", "socket",
    "pipeline", "backend", "frontend", "database", "postgres", "redis", "mongodb",
    "endpoint", "payload", "algorithm", "architecture", "microservice", "harness",
    "agentic", "inference", "prompt", "token", "embedding", "vector", "neural",
}

_FINANCE_KEYWORDS = {
    "revenue", "profit", "margin", "equity", "debt", "valuation", "shares", "dividend",
    "portfolio", "inflation", "balance sheet", "quarterly", "fiscal", "capital", "yield",
}

_LEGAL_KEYWORDS = {
    "agreement", "contract", "parties", "indemnify", "liability", "warranty", "governing law",
    "jurisdiction", "arbitration", "intellectual property", "clause", "statute",
}

_SCIENCE_KEYWORDS = {
    "hypothesis", "theorem", "equation", "quantum", "velocity", "acceleration", "molecule",
    "organism", "cellular", "gravity", "thermodynamics", "entropy", "derivative", "integral",
}


# ── Context Analyzer Engine ────────────────────────────────────────

class ContextAnalyzer:
    """Infers structural type, domain, intent, and grounding from text."""

    @classmethod
    def analyze(cls, text: str, surrounding_hint: Optional[str] = None) -> ContextAnalysis:
        """Analyze text and return a comprehensive ContextAnalysis object.

        Args:
            text: Selected text from user screen or clipboard.
            surrounding_hint: Optional application title or window name.

        Returns:
            ContextAnalysis dataclass.
        """
        if not text or not text.strip():
            return ContextAnalysis(
                domain=ContentDomain.GENERAL,
                content_type=ContentType.SHORT_PHRASE,
                primary_intent=UserIntent.FREEFORM_QUESTION,
                language="en",
                language_name="English",
                confidence=1.0,
                recommended_actions=[ActionKind.ASK_AI, ActionKind.CAPTURE_TEXT, ActionKind.SETTINGS],
            )

        clean = text.strip()
        lines = clean.splitlines()
        word_count = len(clean.split())

        # 1. Check for Acronyms & Short Technical Terms
        clean_upper = clean.upper().strip(" .!?:;'\"`")
        if clean_upper in GROUNDED_ACRONYMS:
            meaning, domain = GROUNDED_ACRONYMS[clean_upper]
            return ContextAnalysis(
                domain=domain,
                content_type=ContentType.ACRONYM_TERM,
                primary_intent=UserIntent.EXPAND_ACRONYM,
                language="en",
                language_name="English",
                confidence=0.98,
                grounded_meaning=meaning,
                keywords=[clean_upper],
                recommended_actions=[
                    ActionKind.EXPLAIN,
                    ActionKind.SEARCH_WEB,
                    ActionKind.ASK_AI,
                    ActionKind.REWRITE,
                ],
            )

        # 2. Check for Error Logs & Stack Traces
        for pattern in _ERROR_PATTERNS:
            if re.search(pattern, clean, re.IGNORECASE | re.MULTILINE):
                return ContextAnalysis(
                    domain=ContentDomain.SOFTWARE_TECH,
                    content_type=ContentType.ERROR_LOG,
                    primary_intent=UserIntent.DEBUG_ERROR,
                    language="en",
                    language_name="English",
                    confidence=0.95,
                    recommended_actions=[
                        ActionKind.EXPLAIN,
                        ActionKind.ASK_AI,
                        ActionKind.SEARCH_WEB,
                        ActionKind.REWRITE,
                    ],
                )

        # 3. Check for Code Snippets
        code_matches = sum(
            1 for p in _CODE_PATTERNS if re.search(p, clean, re.MULTILINE)
        )
        has_indentation = any(l.startswith(("    ", "\t")) for l in lines[1:])
        has_code_syntax = code_matches >= 1 or (has_indentation and len(lines) >= 3)

        if has_code_syntax:
            return ContextAnalysis(
                domain=ContentDomain.SOFTWARE_TECH,
                content_type=ContentType.CODE_SNIPPET,
                primary_intent=UserIntent.EXPLAIN_CONCEPT,
                language="en",
                language_name="English",
                confidence=0.92,
                recommended_actions=[
                    ActionKind.EXPLAIN,
                    ActionKind.REWRITE,
                    ActionKind.ASK_AI,
                    ActionKind.SEARCH_WEB,
                ],
            )

        # 4. Domain Keyword Scoring
        text_lower = clean.lower()
        domain_scores = {
            ContentDomain.SOFTWARE_TECH: sum(1 for w in _TECH_KEYWORDS if re.search(rf"\b{re.escape(w)}\b", text_lower)),
            ContentDomain.BUSINESS_FINANCE: sum(1 for w in _FINANCE_KEYWORDS if re.search(rf"\b{re.escape(w)}\b", text_lower)),
            ContentDomain.LEGAL_COMPLIANCE: sum(1 for w in _LEGAL_KEYWORDS if re.search(rf"\b{re.escape(w)}\b", text_lower)),
            ContentDomain.ACADEMIC_SCIENCE: sum(1 for w in _SCIENCE_KEYWORDS if re.search(rf"\b{re.escape(w)}\b", text_lower)),
        }

        best_domain = ContentDomain.GENERAL
        max_score = 0
        for domain, score in domain_scores.items():
            if score > max_score:
                max_score = score
                best_domain = domain

        # 5. Content Type & Intent Determination
        if word_count > 60 or len(lines) > 4:
            content_type = ContentType.PROSE_ARTICLE
            primary_intent = UserIntent.SUMMARIZE_TEXT
            recommended = [
                ActionKind.SUMMARIZE,
                ActionKind.EXPLAIN,
                ActionKind.REWRITE,
                ActionKind.TRANSLATE,
                ActionKind.SEARCH_WEB,
            ]
        elif clean.endswith("?") or re.match(r"^(how|what|why|where|when|who|is|can|does)\b", text_lower):
            content_type = ContentType.NATURAL_QUERY
            primary_intent = UserIntent.FREEFORM_QUESTION
            recommended = [
                ActionKind.ASK_AI,
                ActionKind.SEARCH_WEB,
                ActionKind.EXPLAIN,
            ]
        elif word_count <= 8:
            content_type = ContentType.SHORT_PHRASE
            primary_intent = UserIntent.EXPLAIN_CONCEPT if best_domain != ContentDomain.GENERAL else UserIntent.SEARCH_INFORMATION
            recommended = [
                ActionKind.EXPLAIN,
                ActionKind.SEARCH_WEB,
                ActionKind.TRANSLATE,
                ActionKind.REWRITE,
                ActionKind.ASK_AI,
            ]
        else:
            content_type = ContentType.PROSE_ARTICLE
            primary_intent = UserIntent.REWRITE_PROSE
            recommended = [
                ActionKind.REWRITE,
                ActionKind.EXPLAIN,
                ActionKind.SUMMARIZE,
                ActionKind.TRANSLATE,
            ]

        confidence = min(0.95, 0.50 + (max_score * 0.15))

        # Script-based Foreign Language Detection
        script_match = None
        if re.search(r"[\u0400-\u04FF]", clean):
            script_match = ("ru", "Russian")
        elif re.search(r"[\u0900-\u097F]", clean):
            script_match = ("hi", "Hindi")
        elif re.search(r"[\u0600-\u06FF\u0750-\u077F]", clean):
            script_match = ("ar", "Arabic")
        elif re.search(r"[\u4E00-\u9FFF]", clean):
            script_match = ("zh", "Chinese")
        elif re.search(r"[\u3040-\u309F\u30A0-\u30FF]", clean):
            script_match = ("ja", "Japanese")
        elif re.search(r"[\uAC00-\uD7AF]", clean):
            script_match = ("ko", "Korean")

        lang = script_match[0] if script_match else "en"
        lang_name = script_match[1] if script_match else "English"
        if script_match:
            recommended = [ActionKind.TRANSLATE, ActionKind.EXPLAIN, ActionKind.ASK_AI]
            primary_intent = UserIntent.TRANSLATE_LANGUAGE

        return ContextAnalysis(
            domain=best_domain,
            content_type=content_type,
            primary_intent=primary_intent,
            language=lang,
            language_name=lang_name,
            confidence=confidence,
            recommended_actions=recommended,
        )


    # ── Context-Aware Prompt Builders ───────────────────────────

    @classmethod
    def build_explain_prompt(cls, text: str, analysis: ContextAnalysis) -> tuple[str, str]:
        """Build a domain-grounded system prompt and user prompt for Explain.

        Returns:
            (prompt, system_prompt)
        """
        domain_name = analysis.domain.value.replace("_", " ").title()

        if analysis.content_type == ContentType.ACRONYM_TERM and analysis.grounded_meaning:
            system_prompt = (
                f"You are a principal technical expert in {domain_name}. "
                "Explain technical concepts with deep accuracy, concise clarity, and practical context. "
                "Avoid vague analogies or generic dictionary definitions. Get straight to what it is, "
                "how it functions, and why it is used."
            )
            prompt = (
                f"Explain the technical acronym '{text}' in the domain of {domain_name}.\n"
                f"Context note: In this domain, '{text}' specifically refers to {analysis.grounded_meaning}.\n\n"
                "Please explain:\n"
                "1. What it stands for and core definition\n"
                "2. How it works fundamentally\n"
                "3. Typical real-world use cases or architecture"
            )
            return prompt, system_prompt

        if analysis.content_type == ContentType.ERROR_LOG:
            system_prompt = (
                "You are an expert software engineer and debugger. "
                "Analyze errors with surgical precision: identify the root cause, "
                "the exact line/component at fault, and provide the concrete fix."
            )
            prompt = (
                f"Analyze the following error / stack trace:\n\n```\n{text}\n```\n\n"
                "Explain:\n"
                "1. Root Cause: What failed and why\n"
                "2. Solution: How to fix it (provide code if applicable)"
            )
            return prompt, system_prompt

        if analysis.content_type == ContentType.CODE_SNIPPET:
            system_prompt = (
                "You are a senior software engineer. Explain code clearly, focusing on its logic, "
                "purpose, time/space complexity, and any edge cases or caveats."
            )
            prompt = (
                f"Explain the following code snippet:\n\n```\n{text}\n```\n\n"
                "Break down what it does step-by-step, its inputs and outputs, and key design decisions."
            )
            return prompt, system_prompt

        # General / domain-specific concept explanation
        system_prompt = (
            f"You are an expert contextual explainer specializing in {domain_name}. "
            "Explain concepts clearly, concisely, and tailored to the technical depth of the text. "
            "Be direct, accurate, and avoid filler."
        )
        prompt = f"Please explain the following {domain_name} concept:\n\n{text}"
        return prompt, system_prompt

    @classmethod
    def build_rewrite_prompt(cls, text: str, analysis: ContextAnalysis) -> tuple[str, str]:
        """Build strict semantic-preserving prompt for Rewrite.

        CONTRACT:
        Preserves: meaning, intent, technical terms, factual claims, qualifiers.
        Only modifies: grammar, clarity, structure, tone, readability.
        FORBIDDEN: inventing info, changing claims, answering text, semantic drift.
        """
        system_prompt = (
            "You are an expert precision editor. Your task is to rewrite the text to improve grammar, "
            "clarity, structure, and professional flow while STRICTLY preserving the original meaning.\n\n"
            "STRICT RULES:\n"
            "1. PRESERVE all technical terminology, claims, numbers, and facts unchanged (e.g. do NOT change 'AI systems' to 'AI research').\n"
            "2. DO NOT alter the user's intended meaning, stance, or qualifiers.\n"
            "3. DO NOT answer questions in the text, invent new information, or add commentary.\n"
            "4. Reply with the rewritten text ONLY. No explanations, markdown preamble, or quotes."
        )
        prompt = f"Rewrite the following text with improved clarity while strictly preserving all terminology and facts:\n\n{text}"
        return prompt, system_prompt

    @classmethod
    def rank_actions(
        cls,
        analysis: Optional[ContextAnalysis],
        has_selection: bool = False,
    ) -> list[ActionKind]:
        """Rank actions adaptively based on context intelligence.

        Returns top recommended ActionKinds to guide user attention.
        """
        if not has_selection or analysis is None:
            return [ActionKind.CAPTURE_TEXT, ActionKind.ASK_AI, ActionKind.SETTINGS]

        if analysis.language and analysis.language != "en":
            return [ActionKind.TRANSLATE, ActionKind.EXPLAIN]

        ct = analysis.content_type
        if ct in (ContentType.ERROR_LOG, ContentType.CODE_SNIPPET):
            return [ActionKind.EXPLAIN, ActionKind.ASK_AI, ActionKind.SEARCH_WEB]

        if ct == ContentType.ACRONYM_TERM:
            return [ActionKind.EXPLAIN, ActionKind.SEARCH_WEB]

        if ct == ContentType.PROSE_ARTICLE:
            return [ActionKind.SUMMARIZE, ActionKind.REWRITE, ActionKind.EXPLAIN]

        if ct == ContentType.NATURAL_QUERY:
            return [ActionKind.ASK_AI, ActionKind.SEARCH_WEB, ActionKind.EXPLAIN]

        if ct == ContentType.SHORT_PHRASE:
            return [ActionKind.EXPLAIN, ActionKind.SEARCH_WEB, ActionKind.REWRITE]

        if analysis.recommended_actions:
            return analysis.recommended_actions[:3]

        return [ActionKind.EXPLAIN, ActionKind.SUMMARIZE, ActionKind.REWRITE]


