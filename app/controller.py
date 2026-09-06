# Cursor Bite — Controller
# ============================================================
# The orchestrator. Everything between "user pressed the hotkey" and
# "here is your result" lives here.
#
#   hotkey  ->  radial menu  ->  action
#                                  |
#                    prepare() on a worker thread
#                    (read the selection, privacy decision)
#                                  |
#                    consent dialog, if the gateway asked for one
#                                  |
#                    execute() on a worker thread
#                                  |
#                            result panel
#
# THREADING RULE:
#   Nothing that can block runs on the UI thread. Reading the selection
#   sleeps on a clipboard poll, Argos loads a model off disk, Ollama
#   takes seconds, and web search waits on the network — all of it goes
#   through run_async(). Dialogs are the mirror image: they may ONLY be
#   opened from the UI thread, which is why the pipeline is split into
#   prepare() and execute() with the controller in between.
#
# CANCELLATION:
#   Work already handed to a worker thread cannot be recalled, so each
#   run carries a generation number. Anything that supersedes it (a new
#   action, Escape, the hotkey) bumps the counter and stale results are
#   dropped on arrival instead of popping up over whatever the user is
#   doing by then.
#
# IMPORTANT: This module does NOT log user content — only action names,
# outcomes, and durations.

from typing import Optional

from PyQt6.QtCore import QObject, QPoint, QRect, pyqtSignal

from app.events import AppEvent, event_bus
from app.pipeline import Pipeline, PreparedRequest
from config.settings import settings
from domain.models import ActionKind, KNOWN_ACTIONS, ProcessingResult
from utils.logger import get_logger
from utils.threading import run_async

logger = get_logger("app.controller")


# ── Action titles ──────────────────────────────────────────────────

_ACTION_TITLES = {action.kind: action.label for action in KNOWN_ACTIONS}

_RESULT_EVENTS = {
    ActionKind.TRANSLATE.value: AppEvent.TRANSLATION_COMPLETED,
    ActionKind.CAPTURE_TEXT.value: AppEvent.OCR_COMPLETED,
    ActionKind.EXPLAIN.value: AppEvent.AI_COMPLETED,
    ActionKind.SUMMARIZE.value: AppEvent.AI_COMPLETED,
    ActionKind.REWRITE.value: AppEvent.AI_COMPLETED,
    ActionKind.ASK_AI.value: AppEvent.AI_COMPLETED,
    ActionKind.SEARCH_WEB.value: AppEvent.SEARCH_COMPLETED,
}


# ── Controller ─────────────────────────────────────────────────────

class Controller(QObject):
    """Coordinates hotkey, radial menu, pipeline, and result display."""

    # ── Signals ─────────────────────────────────────────────────

    menu_opened = pyqtSignal()
    menu_closed = pyqtSignal()

    settings_requested = pyqtSignal()
    """The Settings action was chosen in the menu; the app owns that window."""

    busy_changed = pyqtSignal(bool)
    """True while an action is running, False when the outcome is shown."""

    def __init__(self, parent: QObject = None) -> None:
        super().__init__(parent)

        self._pipeline: Optional[Pipeline] = None
        self._menu = None
        self._panel = None
        self._selector = None

        self._busy = False
        self._generation = 0
        self._capture_title = ""
        self._target_hwnd: Optional[int] = None
        self._pre_captured_text: Optional[str] = None

        self._connect_events()
        logger.info("Controller initialized.")

    def _connect_events(self) -> None:
        """Listen for the hotkey on the event bus."""
        event_bus.hotkey_activated.connect(self.on_hotkey)

    # ── Lazily Built Pieces ─────────────────────────────────────
    #
    # The menu, panel, selector, and pipeline are all built on first
    # use. A session where the user never presses the hotkey therefore
    # never imports Pillow, requests, or Argos.

    @property
    def pipeline(self) -> Pipeline:
        if self._pipeline is None:
            self._pipeline = Pipeline()
        return self._pipeline

    def _get_menu(self):
        """The radial menu, wired up on first creation."""
        if self._menu is None:
            from ui.radial_menu import RadialMenu

            self._menu = RadialMenu()
            self._menu.action_selected.connect(self._on_action_selected)
            self._menu.menu_closed.connect(self._on_menu_closed)
            logger.debug("Radial menu created.")
        return self._menu

    def _get_panel(self):
        """The result panel, created once and reused."""
        if self._panel is None:
            from ui.result_window import ResultWindow

            self._panel = ResultWindow()
            logger.debug("Result panel created.")
        return self._panel

    def _get_selector(self):
        """The region-selection overlay, created once and reused.

        One long-lived instance, not one per capture: the commit path
        emits from inside the selector's own timer callback, so dropping
        the object there would delete a live QWidget mid-slot.
        """
        if self._selector is None:
            from ui.region_selector import RegionSelector

            self._selector = RegionSelector()
            self._selector.region_selected.connect(self._on_region_selected)
            self._selector.cancelled.connect(self._on_region_cancelled)
            logger.debug("Region selector created.")
        return self._selector

    # ── Hotkey ──────────────────────────────────────────────────

    def on_hotkey(self) -> None:
        """Handle a global hotkey press.

        Open the menu, or close it if it is already open. Any result on
        screen is cleared on the way — pressing the hotkey means "I want
        to do something now", not "show me the last answer again".
        """
        if not settings.general_enabled:
            logger.info("Hotkey ignored: Cursor Bite is disabled.")
            return

        if self._menu is not None and self._menu.is_open:
            logger.info("Hotkey pressed while menu open — closing.")
            self.close_menu()
            return

        if self._selector is not None and self._selector.isVisible():
            logger.info("Hotkey pressed during region selection — cancelling.")
            self._selector.cancel()
            return

        self.dismiss_panel()

        # Remember which window had focus before showing our menu
        try:
            import win32gui
            self._target_hwnd = win32gui.GetForegroundWindow()
        except Exception:
            self._target_hwnd = None

        # Pre-capture selection while target app is definitely in foreground
        self._snapshot_selection()

        self._open_menu()

    # ── Menu ────────────────────────────────────────────────────

    def _open_menu(self) -> None:
        """Show the radial menu at the cursor."""
        from domain.context_analyzer import ContextAnalyzer
        from infrastructure.os.cursor import get_cursor_position
        from ui.activation_toast import ActivationToast

        # Brief non-intrusive activation toast
        ActivationToast.show_toast(settings.hotkey_main)

        try:
            cursor_pos = get_cursor_position()
        except Exception as e:
            logger.warning(f"Could not read cursor position: {e}")
            cursor_pos = None

        menu = self._get_menu()

        # Context-aware action ranking
        has_sel = bool(self._pre_captured_text)
        analysis = None
        if has_sel and self._pre_captured_text:
            analysis = ContextAnalyzer.analyze(self._pre_captured_text)
        recommended = ContextAnalyzer.rank_actions(analysis, has_selection=has_sel)
        menu.set_recommended_actions(recommended)

        menu.open_at(cursor_pos, has_selection=has_sel)

        event_bus.emit(AppEvent.RADIAL_MENU_OPENED)
        self.menu_opened.emit()


    def _snapshot_selection(self) -> None:
        """Immediately snapshot current selection while target app is foreground."""
        try:
            res = self.pipeline.text_provider.extract_text(target_hwnd=self._target_hwnd)
            if res.success and res.data and res.data.strip():
                self._pre_captured_text = res.data.strip()
                logger.debug(f"Selection pre-captured ({len(self._pre_captured_text)} chars).")
            else:
                self._pre_captured_text = None
        except Exception as e:
            logger.debug(f"Selection pre-capture skipped: {e}")
            self._pre_captured_text = None

    def close_menu(self) -> None:
        """Close the radial menu if it is open."""
        if self._menu is not None and self._menu.is_open:
            self._menu.close_menu()

    def _on_menu_closed(self) -> None:
        """React to the menu closing, however it was closed."""
        event_bus.emit(AppEvent.RADIAL_MENU_CLOSED)
        self.menu_closed.emit()

    # ── Action Dispatch ─────────────────────────────────────────

    def _on_action_selected(self, action: ActionKind) -> None:
        """Route a chosen menu action."""
        logger.info(f"Action selected: {action.value}")
        event_bus.emit(AppEvent.ACTION_SELECTED, action.value)

        self.close_menu()

        if action == ActionKind.SETTINGS:
            self.settings_requested.emit()
            return

        if self._busy:
            logger.info(f"Action {action.value} ignored: one is already running.")
            return

        self._begin(action)

    def _begin(self, action: ActionKind) -> None:
        """Start a new run of `action`."""
        generation = self._next_generation()
        title = _ACTION_TITLES.get(action, action.value.replace("_", " ").title())

        self._set_busy(True)

        if action == ActionKind.CAPTURE_TEXT:
            self._start_capture(generation, title)
            return

        self._get_panel().show_loading(title, self._cursor_anchor())

        target_hwnd = self._target_hwnd
        cached_text = self._pre_captured_text
        self._pre_captured_text = None

        run_async(
            lambda: self.pipeline.prepare(
                action,
                context_text=cached_text,
                target_hwnd=target_hwnd,
            ),
            on_result=lambda prepared: self._on_prepared(generation, title, prepared),
            on_error=lambda error: self._on_worker_error(generation, title, error),
        )

    # ── Phase Boundary: Consent and Questions ───────────────────

    def _on_prepared(
        self,
        generation: int,
        title: str,
        prepared: object,
    ) -> None:
        """Handle a finished prepare(): ask what needs asking, then execute.

        Runs on the UI thread, which is the whole point of the split —
        this is the only place a dialog may be opened mid-pipeline.
        """
        if not self._is_current(generation):
            logger.debug("Dropping superseded prepare result.")
            return

        if not isinstance(prepared, PreparedRequest):
            self._show_error(title, "The pipeline returned nothing usable.")
            return

        if not prepared.is_ready:
            self._on_prepare_failed(title, prepared)
            return

        if prepared.action == ActionKind.ASK_AI and not prepared.question:
            question = self._ask_question(prepared.text)
            if not question:
                logger.info("Ask AI cancelled: no question entered.")
                self._cancel_run()
                return
            prepared.question = question

        if prepared.requires_consent and not self._confirm_external(title, prepared):
            logger.info(f"External action declined by user: {prepared.action.value}")
            self._show_declined(title)
            return

        # Dialogs hide the panel; bring it back for the actual work.
        self._get_panel().show_loading(title, self._cursor_anchor())

        def _execute_worker(on_token=None, on_status=None):
            return self.pipeline.execute(
                prepared,
                on_token=on_token,
                on_status=on_status,
            )

        run_async(
            _execute_worker,
            on_result=lambda result: self._on_executed(generation, title, result),
            on_error=lambda error: self._on_worker_error(generation, title, error),
            on_token=lambda token: self._on_stream_token(generation, token),
            on_status=lambda status: self._on_stream_status(generation, status),
        )


    def _on_prepare_failed(self, title: str, prepared: PreparedRequest) -> None:
        """Surface a prepare() that couldn't produce anything to work on."""
        if prepared.privacy_decision is not None and prepared.sensitive_types:
            event_bus.emit(
                AppEvent.PRIVACY_BLOCKED,
                prepared.action.value,
                {"sensitive_types": prepared.sensitive_types},
            )

        self._show_error(
            title,
            prepared.error or "No text available to process.",
            meta=self._source_label(prepared.context_source),
        )

    def _ask_question(self, context_text: str) -> Optional[str]:
        """Ask the user what they want to know about the text."""
        from ui.ask_dialog import AskDialog

        self._hide_panel_for_dialog()
        return AskDialog.ask(context_text)

    def _confirm_external(self, title: str, prepared: PreparedRequest) -> bool:
        """Ask before anything leaves the device."""
        from ui.consent_dialog import ConsentDialog

        self._hide_panel_for_dialog()
        return ConsentDialog.ask(
            action_title=title,
            message=prepared.consent_message,
            sensitive_types=prepared.sensitive_types,
            text=prepared.text or "",
        )

    def _hide_panel_for_dialog(self) -> None:
        """Get the panel out of the way before opening a modal dialog.

        The panel is always-on-top; a modal dialog behind it would be
        invisible and unanswerable, which would wedge the whole app.
        """
        if self._panel is not None:
            self._panel.hide()

    # ── Results ─────────────────────────────────────────────────

    def _on_executed(
        self,
        generation: int,
        title: str,
        result: object,
    ) -> None:
        """Render the outcome of execute()."""
        if not self._is_current(generation):
            logger.debug("Dropping superseded action result.")
            return

        if not isinstance(result, ProcessingResult):
            self._show_error(title, "The action returned nothing usable.")
            return

        self._emit_completion(result)

        if not result.success or result.is_empty:
            self._show_error(
                title,
                result.error or "The action produced no result.",
                meta=self._meta_line(result),
            )
            return

        html = self._as_html(result)
        self._get_panel().show_result(
            title,
            result.text,
            meta=self._meta_line(result),
            html=html,
        )
        self._set_busy(False)

    def _on_stream_token(self, generation: int, token: str) -> None:
        """Progressively render streamed tokens in the result panel."""
        if not self._is_current(generation):
            return
        panel = self._get_panel()
        if hasattr(panel, "append_stream_token"):
            panel.append_stream_token(token)

    def _on_stream_status(self, generation: int, status: str) -> None:
        """Update live status indicator on the result panel."""
        if not self._is_current(generation):
            return
        panel = self._get_panel()
        if hasattr(panel, "set_status"):
            panel.set_status(status)

    def _on_worker_error(self, generation: int, title: str, error: Exception) -> None:

        """Report a worker that raised instead of returning."""
        if not self._is_current(generation):
            return

        logger.error(f"Action failed: {title} ({type(error).__name__})")
        event_bus.emit(AppEvent.ERROR, str(error), {"source": "controller"})
        self._show_error(title, "Something went wrong. See the log for details.")

    def _show_error(self, title: str, message: str, meta: str = "") -> None:
        """Show a failure in the panel and end the run."""
        self._get_panel().show_error(title, message, meta=meta)
        self._set_busy(False)

    def _show_declined(self, title: str) -> None:
        """Confirm that a declined external action really did stop here."""
        self._get_panel().show_result(
            title,
            "Nothing was sent. Cursor Bite stopped before this left your device.",
            meta="cancelled",
        )
        self._set_busy(False)

    def _cancel_run(self) -> None:
        """Abandon the current run without saying anything on screen."""
        self._next_generation()
        self.dismiss_panel()
        self._set_busy(False)

    def dismiss_panel(self) -> None:
        """Hide the result panel if it is showing."""
        if self._panel is not None and self._panel.isVisible():
            self._panel.dismiss()

    # ── Screen Capture (OCR) ────────────────────────────────────

    def _start_capture(self, generation: int, title: str) -> None:
        """Check OCR is usable, then let the user drag a region.

        The availability probe runs off-thread and *before* the overlay
        so a user without Tesseract is told so immediately, rather than
        after carefully selecting a region for nothing.
        """
        self._capture_title = title

        run_async(
            lambda: self.pipeline.ocr_provider.is_available(),
            on_result=lambda ok: self._on_ocr_probed(generation, title, ok),
            on_error=lambda error: self._on_worker_error(generation, title, error),
        )

    def _on_ocr_probed(self, generation: int, title: str, available: object) -> None:
        """Open the region selector once OCR is confirmed available."""
        if not self._is_current(generation):
            return

        if not available:
            self._show_error(
                title,
                "OCR is not available. Install Tesseract OCR and make sure "
                "tesseract.exe is on your PATH, then use Check Components "
                "from the tray menu to re-test.",
            )
            return

        self._get_selector().start()

    def _on_region_selected(self, region: QRect) -> None:
        """Capture the chosen region and run it through OCR."""
        generation = self._generation
        title = self._capture_title or _ACTION_TITLES[ActionKind.CAPTURE_TEXT]

        if not self._busy:
            # The run was cancelled while the overlay was still up.
            logger.debug("Region reported after the run ended — ignoring.")
            return

        self._get_panel().show_loading(title, self._cursor_anchor())

        run_async(
            lambda: self._capture_and_prepare(region),
            on_result=lambda prepared: self._on_prepared(generation, title, prepared),
            on_error=lambda error: self._on_worker_error(generation, title, error),
        )

    def _capture_and_prepare(self, region: QRect) -> PreparedRequest:
        """Grab the region and OCR it. Runs on a worker thread.

        The screenshot exists only as bytes in memory — nothing is
        written to disk on this path.
        """
        from infrastructure.os.screen_capture import screen_capture

        image_bytes = screen_capture.capture_absolute_region_to_bytes(
            region.left(), region.top(), region.width(), region.height()
        )

        if not image_bytes:
            return PreparedRequest(
                action=ActionKind.CAPTURE_TEXT,
                error="The screen region could not be captured.",
            )

        return self.pipeline.prepare(ActionKind.CAPTURE_TEXT, image_bytes=image_bytes)

    def _on_region_cancelled(self) -> None:
        """The user aborted the region selection."""
        self._cancel_run()

    # ── Component Status (for the tray dialog) ──────────────────

    def component_status(self) -> dict:
        """Probe every component. Safe to call from a worker thread."""
        return self.pipeline.get_component_status()

    def recheck_components(self) -> dict:
        """Drop cached availability and probe again. Worker-thread safe."""
        return self.pipeline.recheck_components()

    # ── Run Bookkeeping ─────────────────────────────────────────

    def _next_generation(self) -> int:
        """Invalidate any in-flight run and return the new generation."""
        self._generation += 1
        return self._generation

    def _is_current(self, generation: int) -> bool:
        """Whether `generation` is still the run the user is waiting on."""
        return generation == self._generation

    def _set_busy(self, busy: bool) -> None:
        """Track whether an action is running, and tell anyone who cares."""
        if busy == self._busy:
            return
        self._busy = busy
        self.busy_changed.emit(busy)

    # ── Presentation Helpers ────────────────────────────────────

    @staticmethod
    def _cursor_anchor() -> Optional[QPoint]:
        """Where the result panel should appear."""
        from infrastructure.os.cursor import get_cursor_position

        try:
            return get_cursor_position()
        except Exception:
            return None

    @staticmethod
    def _as_html(result: ProcessingResult) -> Optional[str]:
        """Rich rendering for results that benefit from it."""
        if result.metadata.get("action") != ActionKind.SEARCH_WEB.value:
            return None

        results = result.metadata.get("results")
        if not results:
            return None

        from ui.result_window import format_search_html

        return format_search_html(results)

    @staticmethod
    def _meta_line(result: ProcessingResult) -> str:
        """Build the small grey line under the result title."""
        meta = result.metadata
        parts: list[str] = []

        action = meta.get("action")

        if action == ActionKind.TRANSLATE.value:
            source = meta.get("source_lang") or "auto"
            target = meta.get("target_lang") or "?"
            if meta.get("untranslated"):
                parts.append(f"already {target}")
            else:
                parts.append(f"{source} → {target}")
            if meta.get("cached"):
                parts.append("cached")

        elif action == ActionKind.SEARCH_WEB.value:
            count = meta.get("result_count")
            if count:
                parts.append(f"{count} result{'s' if count != 1 else ''}")
            parts.append("DuckDuckGo")

        elif meta.get("model"):
            parts.append(str(meta["model"]))

        if action == ActionKind.CAPTURE_TEXT.value and result.success:
            parts.append(f"{len(result.text)} characters")

        elapsed = result.processing_time_ms
        if elapsed:
            parts.append(
                f"{elapsed / 1000:.1f} s" if elapsed >= 1000 else f"{elapsed} ms"
            )

        return "  ·  ".join(parts)

    @staticmethod
    def _source_label(context_source: str) -> str:
        """Human-readable name for where the text came from."""
        return {
            "selected_text": "from the selection",
            "clipboard": "from the clipboard",
            "ocr": "from the captured region",
            "screen_region": "from the captured region",
            "ui_automation": "from the active window",
        }.get(context_source, "")

    @staticmethod
    def _emit_completion(result: ProcessingResult) -> None:
        """Announce a finished action on the event bus."""
        event = _RESULT_EVENTS.get(result.metadata.get("action"))
        if event is None:
            return

        event_bus.emit(
            event,
            "ok" if result.success else None,
            {"success": result.success},
        )

    # ── State ───────────────────────────────────────────────────

    @property
    def is_busy(self) -> bool:
        """Whether an action is currently running."""
        return self._busy

    @property
    def is_menu_open(self) -> bool:
        """Whether the radial menu is showing."""
        return self._menu is not None and self._menu.is_open

    @property
    def menu(self):
        """The radial menu, or None if it has never been opened."""
        return self._menu

    # ── Shutdown ────────────────────────────────────────────────

    def shutdown(self) -> None:
        """Close everything this controller owns."""
        self._next_generation()

        if self._selector is not None and self._selector.isVisible():
            self._selector.cancel()

        self.close_menu()
        self.dismiss_panel()

        logger.info("Controller shut down.")
