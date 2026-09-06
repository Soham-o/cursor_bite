# Cursor Bite — Threading Helpers
# ============================================================
# Utilities for running work on background threads without
# blocking the UI thread.
#
# Everything the pipeline does can block: Ollama inference takes
# seconds, Argos loads a model off disk, web search waits on the
# network, and the clipboard poll sleeps. Running any of it on the UI
# thread freezes the radial menu and the result panel, so all of it
# goes through run_async() below.

import logging
from typing import Callable, Generic, Optional, TypeVar

from PyQt6.QtCore import QRunnable, QThreadPool, pyqtSignal, QObject

T = TypeVar("T")

logger = logging.getLogger("cursor_bite.utils.threading")


# ── Qt Worker (QRunnable) ──────────────────────────────────────────

class Worker(QRunnable):
    """A QRunnable that executes a function in a thread pool.

    Usage:
        worker = Worker(target=my_function, *args, **kwargs)
        worker.signals.result.connect(handle_result)
        worker.signals.error.connect(handle_error)
        worker.signals.finished.connect(handle_finished)
        QThreadPool.globalInstance().start(worker)
    """

    class Signals(QObject):
        """Signals emitted by the worker."""

        result = pyqtSignal(object)
        error = pyqtSignal(Exception)
        finished = pyqtSignal()
        token = pyqtSignal(str)
        status = pyqtSignal(str)

    def __init__(
        self,
        target: Callable[..., T],
        *args: object,
        **kwargs: object,
    ) -> None:
        super().__init__()
        self.target = target
        self.args = args
        self.kwargs = kwargs
        self.signals = self.Signals()
        self.setAutoDelete(True)

    def run(self) -> None:
        """Execute the target function in a background thread."""
        try:
            import inspect
            extra_kwargs = {}
            try:
                sig = inspect.signature(self.target)
                if "on_token" in sig.parameters:
                    extra_kwargs["on_token"] = self.signals.token.emit
                if "on_status" in sig.parameters:
                    extra_kwargs["on_status"] = self.signals.status.emit
            except Exception:
                pass

            result = self.target(*self.args, **{**self.kwargs, **extra_kwargs})
            self.signals.result.emit(result)
        except Exception as e:
            self.signals.error.emit(e)
        finally:
            self.signals.finished.emit()


# ── Default Thread Pool ────────────────────────────────────────────

_default_pool: Optional[QThreadPool] = None


def get_thread_pool() -> QThreadPool:
    """Get the global thread pool.

    Returns:
        QThreadPool instance with a sensible thread limit.
    """
    global _default_pool
    if _default_pool is None:
        _default_pool = QThreadPool.globalInstance()
        _default_pool.setMaxThreadCount(4)
    return _default_pool


# ── Fire-and-forget Runner ─────────────────────────────────────────

_in_flight: set = set()
"""Workers currently running.

The thread pool owns the C++ runnable, but nothing owns the Python
Worker — without this set it can be garbage collected while still
running, taking its Signals object (and therefore the pending result)
with it. Entries are removed when the worker finishes.
"""


def run_async(
    target: Callable[..., T],
    on_result: Optional[Callable[[object], None]] = None,
    on_error: Optional[Callable[[Exception], None]] = None,
    on_finished: Optional[Callable[[], None]] = None,
    on_token: Optional[Callable[[str], None]] = None,
    on_status: Optional[Callable[[str], None]] = None,
) -> Worker:
    """Run `target` on the thread pool and deliver results to the caller.

    Callbacks fire on the thread that owns the connected receiver — for
    slots on UI objects, that is the UI thread, which is what makes this
    safe to use for showing results.

    Args:
        target: Callable to run. Can optionally accept on_token and on_status kwargs.
        on_result: Called with the return value on success.
        on_error: Called with the exception if `target` raised.
        on_finished: Called after either outcome.
        on_token: Progressively called with tokens for streaming actions.
        on_status: Called when pipeline status changes (e.g. Preparing -> Thinking -> Generating).

    Returns:
        The Worker, already started.
    """
    worker = Worker(target)

    if on_result is not None:
        worker.signals.result.connect(on_result)
    if on_error is not None:
        worker.signals.error.connect(on_error)
    if on_finished is not None:
        worker.signals.finished.connect(on_finished)
    if on_token is not None:
        worker.signals.token.connect(on_token)
    if on_status is not None:
        worker.signals.status.connect(on_status)

    _in_flight.add(worker)
    worker.signals.finished.connect(lambda: _in_flight.discard(worker))

    get_thread_pool().start(worker)
    return worker
