# Cursor Bite — Domain Models
# ============================================================
# Data models representing core domain concepts.
# These are pure data containers with no infrastructure dependencies.

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


# ── Action Types ────────────────────────────────────────────────────

class ActionKind(Enum):
    """Available actions in the Cursor Bite radial menu."""

    TRANSLATE = "translate"
    EXPLAIN = "explain"
    SUMMARIZE = "summarize"
    SEARCH_WEB = "search_web"
    REWRITE = "rewrite"
    ASK_AI = "ask_ai"
    CAPTURE_TEXT = "capture_text"
    SETTINGS = "settings"


# ── Context Source ─────────────────────────────────────────────────

class ContextSource(Enum):
    """Where the input text/content comes from."""

    SELECTED_TEXT = "selected_text"
    CLIPBOARD = "clipboard"
    SCREEN_REGION = "screen_region"
    OCR = "ocr"
    UI_AUTOMATION = "ui_automation"
    IMAGE = "image"
    PDF = "pdf"
    BROWSER = "browser"


# ── Privacy Decision ───────────────────────────────────────────────

class PrivacyDecision(Enum):
    """Result of the Privacy Gateway evaluation."""

    LOCAL_PROCESSING = "local"        # Safe to process locally
    SAFE_EXTERNAL = "safe_external"   # Safe for external processing (with consent)
    BLOCKED = "blocked"               # Contains sensitive data — block
    WARN = "warn"                     # Warn user before proceeding


# ── Context Intelligence Models ───────────────────────────────────

class ContentDomain(Enum):
    """Domain category inferred from content."""

    SOFTWARE_TECH = "software_tech"
    BUSINESS_FINANCE = "business_finance"
    LEGAL_COMPLIANCE = "legal_compliance"
    ACADEMIC_SCIENCE = "academic_science"
    GENERAL = "general"


class ContentType(Enum):
    """Structural type of the content."""

    CODE_SNIPPET = "code_snippet"
    ERROR_LOG = "error_log"
    ACRONYM_TERM = "acronym_term"
    PROSE_ARTICLE = "prose_article"
    NATURAL_QUERY = "natural_query"
    DATA_TABLE = "data_table"
    SHORT_PHRASE = "short_phrase"


class UserIntent(Enum):
    """Inferred user intent for the selected text."""

    EXPLAIN_CONCEPT = "explain_concept"
    DEBUG_ERROR = "debug_error"
    EXPAND_ACRONYM = "expand_acronym"
    SUMMARIZE_TEXT = "summarize_text"
    REWRITE_PROSE = "rewrite_prose"
    TRANSLATE_LANGUAGE = "translate_language"
    SEARCH_INFORMATION = "search_information"
    FREEFORM_QUESTION = "freeform_question"


@dataclass
class ContextAnalysis:
    """Rich semantic analysis of the captured context."""

    domain: ContentDomain = ContentDomain.GENERAL
    content_type: ContentType = ContentType.SHORT_PHRASE
    primary_intent: UserIntent = UserIntent.EXPLAIN_CONCEPT
    language: str = "en"
    language_name: str = "English"
    confidence: float = 0.5
    grounded_meaning: Optional[str] = None
    keywords: list[str] = field(default_factory=list)
    recommended_actions: list[ActionKind] = field(default_factory=list)



# ── Processing Result ──────────────────────────────────────────────

@dataclass
class ProcessingResult:
    """Result of a pipeline processing step."""

    success: bool
    data: Optional[str] = None
    error: Optional[str] = None
    processing_time_ms: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def text(self) -> str:
        """Convenience: return data as string or empty."""
        return self.data or ""

    @property
    def is_empty(self) -> bool:
        return not self.data or not self.data.strip()


# ── Translation Result ─────────────────────────────────────────────

@dataclass
class TranslationResult(ProcessingResult):
    """Result of a translation operation."""

    source_language: Optional[str] = None
    target_language: Optional[str] = None
    original_text: Optional[str] = None


# ── AI Result ──────────────────────────────────────────────────────

@dataclass
class AIResult(ProcessingResult):
    """Result of an AI operation."""

    model: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None


# ── Search Result ──────────────────────────────────────────────────

@dataclass
class SearchResult(ProcessingResult):
    """Result of a web search operation."""

    query: Optional[str] = None
    results: list[dict[str, str]] = field(default_factory=list)
    """Each result: {"title": ..., "url": ..., "snippet": ...}"""


# ── OCR Result ─────────────────────────────────────────────────────

@dataclass
class OCRResult(ProcessingResult):
    """Result of an OCR operation."""

    source_image_size: Optional[tuple[int, int]] = None
    confidence: float = 0.0


# ── Action Definition ──────────────────────────────────────────────

@dataclass
class ActionDefinition:
    """Defines a radial menu action."""

    kind: ActionKind
    label: str
    description: str = ""
    icon: Optional[str] = None
    enabled: bool = True
    requires_text: bool = True
    """If True, the action is disabled when no text is available."""

    def __str__(self) -> str:
        return self.label


# ── Known Actions ──────────────────────────────────────────────────

KNOWN_ACTIONS: list[ActionDefinition] = [
    ActionDefinition(
        kind=ActionKind.TRANSLATE,
        label="Translate",
        description="Translate selected text to English",
        icon="🌐",
        enabled=True,
    ),
    ActionDefinition(
        kind=ActionKind.EXPLAIN,
        label="Explain",
        description="Explain the selected text in simple terms",
        icon="💡",
        enabled=True,
    ),
    ActionDefinition(
        kind=ActionKind.SUMMARIZE,
        label="Summarize",
        description="Summarize the selected text",
        icon="📝",
        enabled=True,
    ),
    ActionDefinition(
        kind=ActionKind.SEARCH_WEB,
        label="Search Web",
        description="Search the web for the selected text",
        icon="🔍",
        enabled=True,
    ),
    ActionDefinition(
        kind=ActionKind.REWRITE,
        label="Rewrite",
        description="Rewrite the selected text",
        icon="✏️",
        enabled=True,
    ),
    ActionDefinition(
        kind=ActionKind.ASK_AI,
        label="Ask AI",
        description="Ask AI about the selected text",
        icon="🤖",
        enabled=True,
    ),
    ActionDefinition(
        kind=ActionKind.CAPTURE_TEXT,
        label="Capture Text",
        description="Capture text from screen region via OCR",
        icon="📸",
        enabled=True,
        requires_text=False,
    ),
    ActionDefinition(
        kind=ActionKind.SETTINGS,
        label="Settings",
        description="Open Cursor Bite settings",
        icon="⚙️",
        enabled=True,
        requires_text=False,
    ),
]
