# Cursor Bite — Pipeline
# ============================================================
# The processing pipeline orchestrates the flow from user action
# to result:
#
#   User Action
#       |
#       v
#   Context Extraction  (selection, clipboard, OCR)
#       |
#       v
#   Privacy Gateway    (sensitive data check)
#       |
#       v
#   Provider Selection  (local vs external)
#       |
#       v
#   Processing          (translation, AI, search, etc.)
#       |
#       v
#   Result Display      (near cursor)
#
# TWO-PHASE EXECUTION:
#   prepare() does extraction + the privacy decision.
#   execute() does the actual work.
#
#   They are split because the privacy gateway can come back with
#   "external, but ask the user first" (PrivacyDecision.WARN). The
#   consent dialog has to run on the UI thread, and the surrounding
#   work has to run off it, so the caller needs a seam between the
#   two. process() composes both phases for callers that don't need
#   the seam.
#
# PROVIDER RESOLUTION IS LAZY AND FAILURE-SAFE:
#   Providers are imported on first access, not at module import, so
#   importing this module does not pull in Pillow, requests or
#   beautifulsoup4. An import that fails resolves to a provider that
#   reports itself unavailable with an actionable hint, so a partial
#   install degrades one action at a time instead of breaking the app.
#
# IMPORTANT: This module does NOT log user content (text, prompts,
# translation results, search queries, clipboard contents).
# Only technical events are logged: action names, durations, errors.

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from config.settings import settings
from domain.action_contracts import ActionContracts
from domain.context_analyzer import ContextAnalyzer
from domain.output_sanitizer import OutputSanitizer
from domain.interfaces import (
    AIProvider,
    OCRProvider,
    SearchProvider,
    TextProvider,
    TranslationProvider,
)
from domain.models import (
    ActionKind,
    AIResult,
    ContextAnalysis,
    ContextSource,
    OCRResult,
    PrivacyDecision,
    ProcessingResult,
    SearchResult,
    TranslationResult,
)
from infrastructure.privacy.gateway import privacy_gateway
from utils.logger import get_logger

logger = get_logger("app.pipeline")


# ── Actions that leave the machine ─────────────────────────────────

EXTERNAL_ACTIONS = frozenset({ActionKind.SEARCH_WEB})
"""Actions that send content off-device.

Translation (Argos), AI (Ollama) and OCR (Tesseract) all run locally,
so they are deliberately NOT in this set — routing them through the
external branch of the privacy gateway would block local processing of
sensitive text, which the gateway exists to permit.
"""


# ── Providers That Could Not Be Loaded ─────────────────────────────

class _UnavailableProvider:
    """Stands in for a provider whose module could not be imported.

    Every optional component already has a well-handled "not available"
    path with an actionable message. A missing pip package joins that
    path instead of raising out of whichever caller happened to touch
    the provider first — otherwise the tray's "Check Components"
    dialog, whose entire job is to report what is missing, is the thing
    that breaks when something is missing.

    Implements enough of all five provider protocols to be substituted
    for any of them; the pipeline only ever calls the methods belonging
    to the slot this instance was created for.
    """

    def __init__(self, label: str, package: str, missing: Optional[str] = None) -> None:
        self._label = label
        self._package = package
        self._missing = missing or package

    def name(self) -> str:
        return f"{self._label} (package not installed)"

    def is_available(self) -> bool:
        return False

    @property
    def unavailable_hint(self) -> str:
        """Why this component is unusable, phrased as something to do.

        Callers prefer this over their own generic hint, which would
        otherwise send the user off installing Tesseract or Ollama when
        the actual problem is a missing Python package.
        """
        return (
            f"The '{self._missing}' Python package is not installed. "
            f"Run: pip install -r requirements.txt"
        )

    def invalidate(self) -> None:
        """Nothing is cached — a missing package stays missing until reinstall."""

    # Each method returns the failure its slot's caller already knows
    # how to render, rather than raising.

    def source(self) -> ContextSource:
        return ContextSource.SELECTED_TEXT

    def extract_text(self) -> ProcessingResult:
        return ProcessingResult(success=False, error=self.unavailable_hint)

    def extract(self) -> ProcessingResult:
        return self.extract_text()

    def recognize(self, image_bytes: bytes) -> OCRResult:
        return OCRResult(success=False, error=self.unavailable_hint)

    def translate(
        self,
        text: str,
        source_lang: Optional[str] = None,
        target_lang: Optional[str] = None,
    ) -> TranslationResult:
        return TranslationResult(
            success=False,
            error=self.unavailable_hint,
            source_language=source_lang,
            target_language=target_lang,
        )

    def detect_language(self, text: str) -> Optional[str]:
        return None

    def supported_languages(self) -> list[str]:
        return []

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> AIResult:
        return AIResult(success=False, error=self.unavailable_hint)

    def list_models(self) -> list[str]:
        return []

    def get_default_model(self) -> str:
        return ""

    def search(self, query: str, max_results: int = 5) -> SearchResult:
        return SearchResult(success=False, error=self.unavailable_hint, query=query)


def _load(loader, label: str, package: str):
    """Import a provider, degrading to a stub if its module won't load.

    Args:
        loader: Callable performing the deferred import.
        label: Human-readable component name for the status dialog.
        package: pip distribution the import needs, named in the hint
            when the failure doesn't identify one itself.

    Returns:
        The provider singleton, or an _UnavailableProvider in its place.
    """
    try:
        return loader()
    except Exception as e:
        # Broader than ImportError on purpose: a DLL that won't load or
        # a module raising at import time leaves the user in exactly the
        # same position as a package that isn't there.
        #
        # ImportError.name is the module that actually failed, which
        # beats the declared package when a provider pulls in more than
        # one (ocr.tesseract needs both pytesseract and Pillow).
        logger.warning(f"{label} provider unavailable: {type(e).__name__}")
        missing = getattr(e, "name", None)
        return _UnavailableProvider(label, package, missing=missing)


# ── Prepared Request ───────────────────────────────────────────────

@dataclass
class PreparedRequest:
    """Output of Pipeline.prepare() — everything execute() needs.

    A prepared request is either ready (text extracted, privacy allows
    it) or carries the reason it isn't, so the caller can surface a
    single failure path.
    """

    action: ActionKind
    text: Optional[str] = None
    question: Optional[str] = None
    error: Optional[str] = None
    context_source: str = ContextSource.SELECTED_TEXT.value
    prepare_time_ms: int = 0
    privacy_decision: Optional[PrivacyDecision] = None
    requires_consent: bool = False
    consent_message: str = ""
    sensitive_types: list[str] = field(default_factory=list)
    context_analysis: Optional[ContextAnalysis] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_ready(self) -> bool:
        """Whether execute() can do real work with this request."""
        if self.action == ActionKind.ASK_AI:
            return self.error is None
        return self.error is None and bool(self.text and self.text.strip())

    def to_failure_result(self) -> ProcessingResult:
        """Build the ProcessingResult for a request that can't proceed."""
        meta: dict[str, Any] = dict(self.metadata)
        meta["action"] = self.action.value
        meta["context_source"] = self.context_source
        if self.privacy_decision is not None:
            meta["privacy_decision"] = self.privacy_decision.value
        if self.sensitive_types:
            meta["sensitive_types"] = self.sensitive_types

        return ProcessingResult(
            success=False,
            error=self.error or "Nothing to process.",
            processing_time_ms=self.prepare_time_ms,
            metadata=meta,
        )


# ── Pipeline ───────────────────────────────────────────────────────

class Pipeline:
    """Main processing pipeline for Cursor Bite.

    Coordinates context extraction, privacy evaluation, and
    processing to deliver results for user actions.

    Every constructor argument is optional — omitted providers resolve
    to the module singletons on first use. Pass fakes in tests.
    """

    def __init__(
        self,
        text_provider: TextProvider = None,
        translation_provider: TranslationProvider = None,
        ocr_provider: OCRProvider = None,
        ai_provider: AIProvider = None,
        search_provider: SearchProvider = None,
    ) -> None:
        self._text_provider_override = text_provider
        self._translation_provider_override = translation_provider
        self._ocr_provider_override = ocr_provider
        self._ai_provider_override = ai_provider
        self._search_provider_override = search_provider

    # ── Lazily Resolved Providers ───────────────────────────────
    #
    # Each import is deferred and failure-safe: a machine missing an
    # optional package gets a provider that reports itself unavailable,
    # never an ImportError raised from whatever touched it first.

    @property
    def text_provider(self) -> TextProvider:
        if self._text_provider_override is None:
            def load():
                from infrastructure.os.selected_text import selected_text_provider
                return selected_text_provider

            self._text_provider_override = _load(load, "Selection Capture", "pyperclip")
        return self._text_provider_override

    @property
    def translation_provider(self) -> TranslationProvider:
        if self._translation_provider_override is None:
            def load():
                from infrastructure.translation.argos import argos_translator
                return argos_translator

            self._translation_provider_override = _load(
                load, "Translation", "argostranslate"
            )
        return self._translation_provider_override

    @property
    def ocr_provider(self) -> OCRProvider:
        if self._ocr_provider_override is None:
            def load():
                from infrastructure.ocr.tesseract import tesseract_ocr
                return tesseract_ocr

            self._ocr_provider_override = _load(load, "OCR", "pytesseract")
        return self._ocr_provider_override

    @property
    def ai_provider(self) -> AIProvider:
        if self._ai_provider_override is None:
            def load():
                from infrastructure.ai.ollama import ollama_ai
                return ollama_ai

            self._ai_provider_override = _load(load, "Local AI", "requests")
        return self._ai_provider_override

    @property
    def search_provider(self) -> SearchProvider:
        if self._search_provider_override is None:
            def load():
                from infrastructure.search.web_search import web_search
                return web_search

            self._search_provider_override = _load(load, "Web Search", "beautifulsoup4")
        return self._search_provider_override

    # ── Phase 1: Prepare ────────────────────────────────────────

    def prepare(
        self,
        action: ActionKind,
        context_text: Optional[str] = None,
        image_bytes: Optional[bytes] = None,
        question: Optional[str] = None,
        target_hwnd: Optional[int] = None,
    ) -> PreparedRequest:
        """Extract context and run the privacy decision.

        Safe to call from a worker thread — touches no UI.

        Args:
            action: The action to perform.
            context_text: Pre-extracted text (skips extraction).
            image_bytes: Image data for OCR-based actions.
            question: The user's question, for ASK_AI.
            target_hwnd: Optional HWND of window to extract text from.

        Returns:
            PreparedRequest — check .is_ready before calling execute().
        """
        start_time = time.time()
        logger.info(f"Pipeline prepare: action={action.value}")

        source = ContextSource.SELECTED_TEXT.value
        extract_error: Optional[str] = None

        # Step 1: get text
        if context_text is None:
            if image_bytes is not None:
                context_text, extract_error = self._ocr_extract(image_bytes)
                source = ContextSource.OCR.value
            else:
                context_text, extract_error, source = self._extract_text(target_hwnd=target_hwnd)
        else:
            source = ContextSource.SELECTED_TEXT.value

        if not context_text or not context_text.strip():
            if action == ActionKind.ASK_AI:
                context_text = ""
            else:
                elapsed = int((time.time() - start_time) * 1000)
                logger.info(f"Pipeline prepare: no text available ({elapsed}ms)")
                return PreparedRequest(
                    action=action,
                    question=question,
                    error=extract_error or "No text available to process.",
                    context_source=source,
                    prepare_time_ms=elapsed,
                )

        # Step 2: privacy evaluation
        requires_external = self.action_requires_external(action)
        privacy_result = privacy_gateway.evaluate(
            context_text,
            action_name=action.value,
            requires_external=requires_external,
        )

        sensitive_types = list(dict.fromkeys(
            m.sensitive_type.value for m in privacy_result.sensitive_matches
        ))
        elapsed = int((time.time() - start_time) * 1000)

        if privacy_result.is_blocked:
            logger.info(f"Pipeline blocked by privacy gateway ({elapsed}ms)")
            return PreparedRequest(
                action=action,
                question=question,
                error=privacy_result.reason or "Blocked by the Privacy Gateway.",
                context_source=source,
                prepare_time_ms=elapsed,
                privacy_decision=privacy_result.decision,
                sensitive_types=sensitive_types,
            )

        analyzed_text = privacy_result.text or context_text
        context_analysis = None
        if analyzed_text and analyzed_text.strip():
            try:
                context_analysis = ContextAnalyzer.analyze(analyzed_text)
            except Exception as e:
                logger.debug(f"Context analysis failed: {e}")

        return PreparedRequest(
            action=action,
            text=analyzed_text,
            question=question,
            context_source=source,
            prepare_time_ms=elapsed,
            privacy_decision=privacy_result.decision,
            requires_consent=privacy_result.requires_consent,
            consent_message=privacy_result.consent_message,
            sensitive_types=sensitive_types,
            context_analysis=context_analysis,
        )

    # ── Phase 2: Execute ────────────────────────────────────────

    def execute(
        self,
        prepared: PreparedRequest,
        on_token: Optional[Callable[[str], None]] = None,
        on_status: Optional[Callable[[str], None]] = None,
    ) -> ProcessingResult:
        """Run the action described by a prepared request.

        Supports progressive streaming of tokens via on_token callback.
        Safe to call from a worker thread — touches no UI.
        """
        if not prepared.is_ready:
            return prepared.to_failure_result()

        start_time = time.time()

        try:
            result = self._execute_action(
                prepared,
                on_token=on_token,
                on_status=on_status,
            )
        except Exception as e:
            logger.error(f"Pipeline action execution failed: {type(e).__name__}")
            result = ProcessingResult(
                success=False,
                error="Action execution failed.",
            )

        elapsed = int((time.time() - start_time) * 1000)
        result.processing_time_ms = prepared.prepare_time_ms + elapsed

        result.metadata.setdefault("action", prepared.action.value)
        result.metadata.setdefault("context_source", prepared.context_source)
        if prepared.privacy_decision is not None:
            result.metadata.setdefault(
                "privacy_decision", prepared.privacy_decision.value
            )
        if prepared.context_analysis is not None:
            result.metadata.setdefault(
                "domain", prepared.context_analysis.domain.value
            )
            result.metadata.setdefault(
                "content_type", prepared.context_analysis.content_type.value
            )

        status = "completed" if result.success else "failed"
        logger.info(
            f"Pipeline {status}: {prepared.action.value} "
            f"({result.processing_time_ms}ms)"
        )

        return result

    # ── Single-shot Entry Point ─────────────────────────────────

    def process(
        self,
        action: ActionKind,
        context_text: Optional[str] = None,
        image_bytes: Optional[bytes] = None,
        question: Optional[str] = None,
    ) -> ProcessingResult:
        """Prepare and execute in one call.

        Consent is NOT collected — a request that requires consent is
        executed as-is, since there is no UI thread to ask on. Use
        prepare()/execute() when a consent prompt is possible.
        """
        prepared = self.prepare(
            action,
            context_text=context_text,
            image_bytes=image_bytes,
            question=question,
        )
        return self.execute(prepared)

    # ── Text Extraction ─────────────────────────────────────────

    def _extract_text(self, target_hwnd: Optional[int] = None) -> tuple[Optional[str], Optional[str], str]:
        """Extract text from the current context.

        Returns:
            (text, error, context_source)
        """
        source = ContextSource.SELECTED_TEXT.value
        try:
            try:
                result = self.text_provider.extract_text(target_hwnd=target_hwnd)
            except TypeError:
                result = self.text_provider.extract_text()
            source = result.metadata.get("context_source", source)

            if result.success and result.data:
                logger.info(f"Text extracted successfully (source={source}).")
                return result.data.strip(), None, source

            logger.info("Text extraction returned no text.")
            return None, result.error, source
        except Exception as e:
            logger.warning(f"Text extraction failed: {type(e).__name__}")
            return None, "Could not read text from the active window.", source

    def _ocr_extract(self, image_bytes: bytes) -> tuple[Optional[str], Optional[str]]:
        """Extract text from an image using OCR.

        Returns:
            (text, error)
        """
        provider = self.ocr_provider

        if not provider.is_available():
            logger.warning("OCR not available.")
            return None, getattr(provider, "unavailable_hint", "") or (
                "OCR is not available. Install Tesseract OCR and make sure "
                "tesseract.exe is on your PATH."
            )

        try:
            result = provider.recognize(image_bytes)
            if result.success and result.data:
                logger.info(f"OCR extracted text: {len(result.data)} characters.")
                return result.data.strip(), None
            logger.info("OCR returned no text.")
            return None, result.error or "No text found in the captured region."
        except Exception as e:
            logger.warning(f"OCR extraction failed: {type(e).__name__}")
            return None, "OCR failed on the captured region."

    # ── Action Execution ────────────────────────────────────────

    def _execute_action(
        self,
        prepared: PreparedRequest,
        on_token: Optional[Callable[[str], None]] = None,
        on_status: Optional[Callable[[str], None]] = None,
    ) -> ProcessingResult:
        """Dispatch to the handler for the prepared action."""
        action = prepared.action
        text = prepared.text or ""
        analysis = prepared.context_analysis or ContextAnalyzer.analyze(text)

        if action == ActionKind.TRANSLATE:
            return self._action_translate(text)

        if action == ActionKind.EXPLAIN:
            return self._action_explain(text, analysis, on_token=on_token, on_status=on_status)

        if action == ActionKind.SUMMARIZE:
            return self._action_summarize(text, analysis, on_token=on_token, on_status=on_status)

        if action == ActionKind.REWRITE:
            return self._action_rewrite(text, analysis, on_token=on_token, on_status=on_status)

        if action == ActionKind.ASK_AI:
            return self._action_ask(text, prepared.question, analysis, on_token=on_token, on_status=on_status)

        if action == ActionKind.SEARCH_WEB:
            return self._action_search(text)

        if action == ActionKind.CAPTURE_TEXT:
            # The OCR already happened in prepare(); the captured text
            # *is* the result.
            return ProcessingResult(success=True, data=text)

        return ProcessingResult(success=False, error=f"Unknown action: {action.value}")

    def _action_translate(self, text: str) -> ProcessingResult:
        """Translate text into the configured target language."""
        from infrastructure.storage.cache import cache

        provider = self.translation_provider
        target = settings.translation_default_target or "en"

        source_lang = None
        if settings.translation_auto_detect:
            source_lang = provider.detect_language(text)

        if source_lang and source_lang == target:
            logger.info("Translation skipped — text is already in the target language.")
            return ProcessingResult(
                success=True,
                data=text,
                metadata={
                    "source_lang": source_lang,
                    "target_lang": target,
                    "untranslated": True,
                },
            )

        # The cache holds user text in memory. With no-data-retention on,
        # skip it entirely rather than trading privacy for speed.
        may_cache = privacy_gateway.policies.should_retain_text()

        if may_cache:
            cache_key = cache.translation_cache_key(text, source_lang or "auto", target)
            cached = cache.get(cache_key)
            if cached:
                logger.info("Translation served from cache.")
                return ProcessingResult(
                    success=True,
                    data=cached,
                    metadata={
                        "cached": True,
                        "source_lang": source_lang,
                        "target_lang": target,
                    },
                )

        result = provider.translate(
            text=text,
            source_lang=source_lang,
            target_lang=target,
        )

        if may_cache and result.success and result.data:
            cache.set_translation(text, source_lang or "auto", target, result.data)

        if not result.success and not provider.is_available() and self.ai_provider and self.ai_provider.is_available():
            # Fallback to local AI translation if offline provider is not available
            target_name = getattr(provider, "LANGUAGE_NAMES", {}).get(target, target.upper())
            prompt, sys_prompt = ActionContracts.build_translate_contract(text, target, target_name)
            ai_res = self._generate(prompt=prompt, system_prompt=sys_prompt, temperature=0.2, label="translate")
            if ai_res.success and ai_res.data:
                cleaned_trans = OutputSanitizer.sanitize(ActionKind.TRANSLATE, ai_res.data, original_input=text)
                return ProcessingResult(
                    success=True,
                    data=cleaned_trans,
                    metadata={
                        "source_lang": source_lang or "auto",
                        "target_lang": target,
                        "provider": "ollama_fallback",
                    },
                )

        return ProcessingResult(
            success=result.success,
            data=result.data,
            error=result.error,
            metadata={
                "source_lang": result.source_language,
                "target_lang": result.target_language or target,
            },
        )

    def _action_explain(
        self,
        text: str,
        analysis: ContextAnalysis,
        on_token: Optional[Callable[[str], None]] = None,
        on_status: Optional[Callable[[str], None]] = None,
    ) -> ProcessingResult:
        """Explain text with domain grounding and concise 2-4 sentence contract."""
        prompt, system_prompt = ActionContracts.build_explain_contract(text, analysis)
        res = self._generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=settings.ai_temperature,
            label="explain",
            on_token=on_token,
            on_status=on_status,
        )
        if res.success and res.data:
            res.data = OutputSanitizer.sanitize(ActionKind.EXPLAIN, res.data, original_input=text)
        return res

    def _action_summarize(
        self,
        text: str,
        analysis: ContextAnalysis,
        on_token: Optional[Callable[[str], None]] = None,
        on_status: Optional[Callable[[str], None]] = None,
    ) -> ProcessingResult:
        """Summarize text using strict deterministic compression contract."""
        prompt, system_prompt = ActionContracts.build_summarize_contract(text, analysis)
        res = self._generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.3,
            label="summarize",
            on_token=on_token,
            on_status=on_status,
        )
        if res.success and res.data:
            sanitized = OutputSanitizer.sanitize(ActionKind.SUMMARIZE, res.data, original_input=text)
            if OutputSanitizer.is_contract_breached(ActionKind.SUMMARIZE, sanitized):
                # Single-shot correction retry if model violated contract
                corr_prompt, corr_sys = OutputSanitizer.build_correction_prompt(ActionKind.SUMMARIZE, res.data, text)
                retry_res = self._generate(prompt=corr_prompt, system_prompt=corr_sys, temperature=0.2, label="summarize_retry")
                if retry_res.success and retry_res.data:
                    sanitized = OutputSanitizer.sanitize(ActionKind.SUMMARIZE, retry_res.data, original_input=text)
            res.data = sanitized
        return res

    def _action_rewrite(
        self,
        text: str,
        analysis: ContextAnalysis,
        on_token: Optional[Callable[[str], None]] = None,
        on_status: Optional[Callable[[str], None]] = None,
    ) -> ProcessingResult:
        """Rewrite text with strict semantic preservation and zero chat filler."""
        prompt, system_prompt = ActionContracts.build_rewrite_contract(text, analysis)
        res = self._generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.3,
            label="rewrite",
            on_token=on_token,
            on_status=on_status,
        )
        if res.success and res.data:
            sanitized = OutputSanitizer.sanitize(ActionKind.REWRITE, res.data, original_input=text)
            if OutputSanitizer.is_contract_breached(ActionKind.REWRITE, sanitized):
                # Single-shot correction retry if model violated contract
                corr_prompt, corr_sys = OutputSanitizer.build_correction_prompt(ActionKind.REWRITE, res.data, text)
                retry_res = self._generate(prompt=corr_prompt, system_prompt=corr_sys, temperature=0.2, label="rewrite_retry")
                if retry_res.success and retry_res.data:
                    sanitized = OutputSanitizer.sanitize(ActionKind.REWRITE, retry_res.data, original_input=text)
            res.data = sanitized
        return res

    def _action_ask(
        self,
        text: str,
        question: Optional[str],
        analysis: ContextAnalysis,
        on_token: Optional[Callable[[str], None]] = None,
        on_status: Optional[Callable[[str], None]] = None,
    ) -> ProcessingResult:
        """Answer the user's question directly based on context."""
        if not question or not question.strip():
            return ProcessingResult(
                success=False,
                error="No question provided.",
            )

        prompt, system_prompt = ActionContracts.build_ask_contract(text, question, analysis)
        res = self._generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=settings.ai_temperature,
            label="ask_ai",
            on_token=on_token,
            on_status=on_status,
        )
        if res.success and res.data:
            res.data = OutputSanitizer.sanitize(ActionKind.ASK_AI, res.data, original_input=text)
        return res

    def _action_search(self, text: str) -> ProcessingResult:
        """Search the web for the text."""
        provider = self.search_provider
        query = self._to_query(text)

        try:
            search_result = provider.search(query, max_results=5)

            if search_result.success and search_result.results:
                return ProcessingResult(
                    success=True,
                    data=self._format_search_results(search_result.results),
                    metadata={
                        "result_count": len(search_result.results),
                        "results": search_result.results,
                        "query": query,
                    },
                )

            return ProcessingResult(
                success=search_result.success,
                data=search_result.text or "No search results found.",
                error=search_result.error,
                metadata={"query": query},
            )
        except Exception as e:
            logger.error(f"Search failed: {type(e).__name__}")
            return ProcessingResult(success=False, error="Search failed.")

    # ── AI Helper ───────────────────────────────────────────────

    def _generate(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float,
        label: str,
        on_token: Optional[Callable[[str], None]] = None,
        on_status: Optional[Callable[[str], None]] = None,
    ) -> ProcessingResult:
        """Shared AI call path for explain / summarize / rewrite / ask with streaming."""
        if not settings.ai_enabled:
            return ProcessingResult(
                success=False,
                error="AI features are turned off. Enable them in Settings → AI.",
            )

        provider = self.ai_provider
        if provider is None or not provider.is_available():
            return ProcessingResult(
                success=False,
                error=getattr(provider, "unavailable_hint", "") or (
                    "AI is not available. Install Ollama, start it, and pull a "
                    "model (for example: ollama pull llama3.2)."
                ),
            )

        if on_status:
            on_status("Thinking...")

        has_streamed = False

        def wrapped_token(token: str) -> None:
            nonlocal has_streamed
            if not has_streamed:
                has_streamed = True
                if on_status:
                    on_status("Generating...")
            if on_token:
                on_token(token)

        try:
            if hasattr(provider, "generate_stream"):
                result = provider.generate_stream(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    on_token=wrapped_token if on_token else None,
                )
            else:
                result = provider.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=temperature,
                )
            return ProcessingResult(
                success=result.success,
                data=result.data,
                error=result.error,
                metadata={"model": result.model},
            )
        except Exception as e:
            logger.error(f"AI {label} failed: {type(e).__name__}")
            return ProcessingResult(success=False, error=f"AI {label} failed.")

    # ── Helpers ─────────────────────────────────────────────────

    @staticmethod
    def action_requires_external(action: ActionKind) -> bool:
        """Whether an action sends content off-device."""
        return action in EXTERNAL_ACTIONS

    @staticmethod
    def _to_query(text: str) -> str:
        """Collapse a selection into something usable as a search query.

        Search engines reject or mangle very long multi-line queries, so
        this keeps the first line and caps the length.
        """
        first_line = text.strip().splitlines()[0] if text.strip() else ""
        query = " ".join(first_line.split())
        return query[:300]

    @staticmethod
    def _format_search_results(results: list[dict]) -> str:
        """Render search results as readable plain text."""
        formatted = []
        for i, r in enumerate(results, 1):
            snippet = (r.get("snippet") or "").strip()
            if len(snippet) > 220:
                snippet = snippet[:220].rstrip() + "…"
            block = f"{i}. {r.get('title', 'Untitled')}\n   {r.get('url', '')}"
            if snippet:
                block += f"\n   {snippet}"
            formatted.append(block)
        return "\n\n".join(formatted)

    # ── Component Status ────────────────────────────────────────

    def get_component_status(self) -> dict:
        """Get the status of all pipeline components.

        Touching a provider here triggers its lazy validation, which is
        the point — this powers the tray's "Check Components" dialog.
        Each entry carries a `hint` for whatever is missing.
        """
        def probe(provider, hint: str) -> dict:
            try:
                available = provider.is_available()
                # A provider that knows why it is unusable gives a better
                # answer than the generic hint — "install this package"
                # rather than "install Tesseract", when the missing piece
                # is the Python wrapper and not the engine.
                own_hint = getattr(provider, "unavailable_hint", "")
                return {
                    "name": provider.name(),
                    "available": available,
                    "hint": "" if available else (own_hint or hint),
                }
            except Exception as e:
                return {
                    "name": getattr(provider, "__class__", type(provider)).__name__,
                    "available": False,
                    "hint": f"Probe failed: {type(e).__name__}",
                }

        status = {
            "text": probe(
                self.text_provider,
                "Selection capture is unavailable.",
            ),
            "translation": probe(
                self.translation_provider,
                "Install Argos language packs (see SETUP_GUIDE.md step 15).",
            ),
            "ocr": probe(
                self.ocr_provider,
                "Install Tesseract OCR (see SETUP_GUIDE.md).",
            ),
            "ai": probe(
                self.ai_provider,
                "Install and start Ollama, then: ollama pull llama3.2",
            ),
            "search": probe(
                self.search_provider,
                "No internet connection, or DuckDuckGo is unreachable.",
            ),
            "privacy_gateway": {
                "name": "Privacy Gateway",
                "available": True,
                "hint": "",
                "offline_mode": settings.privacy_offline_mode,
            },
        }

        if settings.privacy_offline_mode:
            status["search"]["available"] = False
            status["search"]["hint"] = "Blocked: Offline Mode is on."

        if not settings.ai_enabled:
            status["ai"]["available"] = False
            status["ai"]["hint"] = "Turned off in Settings → AI."

        return status

    def recheck_components(self) -> dict:
        """Drop cached availability checks, then re-probe everything."""
        # Resolved through the properties, not the raw override slots: a
        # provider that has never been touched here may still have been
        # imported (and cached its availability) elsewhere, and it is
        # exactly those stale answers the user is asking us to drop.
        for provider in (
            self.text_provider,
            self.translation_provider,
            self.ocr_provider,
            self.ai_provider,
            self.search_provider,
        ):
            invalidate = getattr(provider, "invalidate", None)
            if callable(invalidate):
                invalidate()
        logger.info("Component availability caches invalidated.")
        return self.get_component_status()
