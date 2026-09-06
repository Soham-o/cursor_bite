# Cursor Bite — Ollama AI Provider
# ============================================================
# Uses Ollama for local LLM inference.
#
# LAZY INITIALIZATION: No connection check on import.
# The first call to is_available() or generate() triggers a check.
#
# Ollama runs on localhost:11434. All processing is local.

import json
import logging
from typing import Callable, Optional

import requests


from config.settings import settings
from domain.models import AIResult
from infrastructure.ai.base import BaseAIProvider
from utils.logger import get_logger

logger = get_logger("infrastructure.ai.ollama")

OLLAMA_DEFAULT_HOST = "http://localhost:11434"
OLLAMA_TIMEOUT = 60
"""Fallback request timeout. `ai.timeout_seconds` in config.json wins."""

OLLAMA_MIN_TIMEOUT = 5
"""Floor for the configured timeout — a 0/negative value would fail instantly."""


# ── Ollama AI Provider ─────────────────────────────────────────────

class OllamaAIProvider(BaseAIProvider):
    """Ollama implementation with lazy initialization.

    No connection check is performed on __init__. The first call to
    is_available() or generate() triggers a check.
    """

    def __init__(self, host: str = OLLAMA_DEFAULT_HOST) -> None:
        self._host = host.rstrip("/")
        self._available: Optional[bool] = None
        self._models: list[str] = []
        self._default_model: str = "llama3.2"
        self._validated: bool = False
        self._model_pinned: bool = False
        """True once set_model() succeeded — stops config from overriding it."""

    # ── Configuration ───────────────────────────────────────────

    @staticmethod
    def _timeout() -> int:
        """Request timeout from config, with a sane floor."""
        try:
            return max(OLLAMA_MIN_TIMEOUT, settings.ai_timeout_seconds)
        except Exception:
            return OLLAMA_TIMEOUT

    def _resolve_model(self) -> None:
        """Pick the model to use from the installed list.

        Preference order:
          1. A model explicitly chosen via set_model()
          2. `ai.model` from config.json — matched exactly, or on the
             name before the ':' tag so "llama3.2" finds "llama3.2:latest"
          3. The first installed model
        """
        if not self._models:
            return

        if self._model_pinned and self._default_model in self._models:
            return

        configured = ""
        try:
            configured = (settings.ai_model or "").strip()
        except Exception:
            configured = ""

        if configured:
            if configured in self._models:
                self._default_model = configured
                return
            for installed in self._models:
                if installed.split(":", 1)[0] == configured.split(":", 1)[0]:
                    self._default_model = installed
                    logger.info(
                        f"Configured model '{configured}' matched installed '{installed}'."
                    )
                    return
            logger.warning(
                f"Configured model '{configured}' is not installed. "
                f"Falling back to '{self._models[0]}'. "
                f"Pull it with: ollama pull {configured}"
            )

        self._default_model = self._models[0]

    # ── Lazy Validation ─────────────────────────────────────────

    def _ensure_ready(self) -> bool:
        """Lazy validation — called on first use."""
        if self._validated:
            return self._available or False

        self._validated = True

        try:
            response = requests.get(
                f"{self._host}/api/tags",
                timeout=5,
            )
            if response.status_code == 200:
                data = response.json()
                self._models = [m["name"] for m in data.get("models", [])]
                self._available = True
                self._resolve_model()
                logger.info(
                    f"Ollama available. Models ({len(self._models)}): "
                    f"{', '.join(self._models) if self._models else 'none installed'}. "
                    f"Using: {self._default_model}"
                )
                return True
            else:
                self._available = False
                logger.info(f"Ollama returned status {response.status_code}.")
                return False
        except requests.ConnectionError:
            self._available = False
            logger.info("Ollama is not running. Start Ollama to use AI features.")
            return False
        except Exception as e:
            self._available = False
            logger.warning(f"Ollama validation failed: {e}")
            return False

    # ── Interface Implementation ────────────────────────────────

    def name(self) -> str:
        return "Ollama (Local AI)"

    def is_available(self) -> bool:
        return self._ensure_ready()

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AIResult:
        """Generate a response. Lazy initialization on first call."""
        if not self._ensure_ready():
            return AIResult(
                success=False,
                error="Ollama is not available. Start Ollama to use AI features.",
            )

        if not prompt or not prompt.strip():
            return AIResult(success=False, error="No prompt provided.")

        max_prompt_length = 8000
        if len(prompt) > max_prompt_length:
            prompt = prompt[:max_prompt_length]

        payload = {
            "model": self._default_model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }

        if system_prompt:
            payload["system"] = system_prompt

        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        timeout = self._timeout()

        try:
            logger.info(f"AI request sent to Ollama (model: {self._default_model}).")

            response = requests.post(
                f"{self._host}/api/generate",
                json=payload,
                timeout=timeout,
            )

            if response.status_code == 200:
                data = response.json()
                generated_text = data.get("response", "").strip()

                if generated_text:
                    logger.info(f"AI response received: {len(generated_text)} characters.")
                    return AIResult(
                        success=True,
                        data=generated_text,
                        model=self._default_model,
                    )
                else:
                    logger.warning("Ollama returned an empty response.")
                    return AIResult(
                        success=False,
                        error="Ollama returned an empty response.",
                        model=self._default_model,
                    )
            elif response.status_code == 404:
                return AIResult(
                    success=False,
                    error=f"Model '{self._default_model}' not found. Pull it with: ollama pull {self._default_model}",
                    model=self._default_model,
                )
            else:
                error_text = response.text[:200] if response.text else "Unknown error"
                return AIResult(
                    success=False,
                    error=f"Ollama API error ({response.status_code}): {error_text}",
                    model=self._default_model,
                )

        except requests.Timeout:
            logger.error("Ollama request timed out.")
            return AIResult(
                success=False,
                error=(
                    f"Request timed out after {timeout} seconds. "
                    f"Raise ai.timeout_seconds in config.json for larger models."
                ),
                model=self._default_model,
            )
        except requests.ConnectionError:
            logger.error("Lost connection to Ollama.")
            self._available = False
            return AIResult(
                success=False,
                error="Connection to Ollama was lost.",
                model=self._default_model,
            )
        except Exception as e:
            logger.error(f"AI generation failed: {e}")
            return AIResult(
                success=False,
                error=f"AI generation failed: {str(e)}",
                model=self._default_model,
            )

    def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        on_token: Optional[Callable[[str], None]] = None,
    ) -> AIResult:
        """Generate response with token streaming."""
        if on_token is None:
            return self.generate(prompt, system_prompt, temperature, max_tokens)

        if not self._ensure_ready():
            return AIResult(
                success=False,
                error="Ollama is not available. Start Ollama to use AI features.",
            )

        if not prompt or not prompt.strip():
            return AIResult(success=False, error="No prompt provided.")

        max_prompt_length = 8000
        if len(prompt) > max_prompt_length:
            prompt = prompt[:max_prompt_length]

        payload = {
            "model": self._default_model,
            "prompt": prompt,
            "stream": True,
            "options": {"temperature": temperature},
        }

        if system_prompt:
            payload["system"] = system_prompt

        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        timeout = self._timeout()

        try:
            logger.info(f"AI streaming request sent to Ollama (model: {self._default_model}).")

            response = requests.post(
                f"{self._host}/api/generate",
                json=payload,
                stream=True,
                timeout=timeout,
            )

            if response.status_code == 200:
                chunks: list[str] = []
                for line in response.iter_lines():
                    if line:
                        try:
                            data = json.loads(line.decode("utf-8"))
                            token = data.get("response", "")
                            if token:
                                chunks.append(token)
                                on_token(token)
                        except Exception:
                            continue

                full_text = "".join(chunks).strip()
                if full_text:
                    return AIResult(
                        success=True,
                        data=full_text,
                        model=self._default_model,
                    )
                else:
                    return AIResult(
                        success=False,
                        error="Ollama returned an empty response.",
                        model=self._default_model,
                    )
            elif response.status_code == 404:
                return AIResult(
                    success=False,
                    error=f"Model '{self._default_model}' not found. Pull it with: ollama pull {self._default_model}",
                    model=self._default_model,
                )
            else:
                error_text = response.text[:200] if response.text else "Unknown error"
                return AIResult(
                    success=False,
                    error=f"Ollama API error ({response.status_code}): {error_text}",
                    model=self._default_model,
                )

        except requests.Timeout:
            logger.error("Ollama streaming request timed out.")
            return AIResult(
                success=False,
                error=f"Request timed out after {timeout} seconds.",
                model=self._default_model,
            )
        except requests.ConnectionError:
            logger.error("Lost connection to Ollama.")
            self._available = False
            return AIResult(
                success=False,
                error="Connection to Ollama was lost.",
                model=self._default_model,
            )
        except Exception as e:
            logger.error(f"AI streaming generation failed: {e}")
            return AIResult(
                success=False,
                error=f"AI generation failed: {str(e)}",
                model=self._default_model,
            )

    def list_models(self) -> list[str]:
        """List available Ollama models."""
        if not self._ensure_ready():
            return []
        return list(self._models)

    def get_default_model(self) -> str:
        """Get the default model name."""
        return self._default_model

    def set_model(self, model_name: str) -> bool:
        """Set the default model.

        A successful call pins the choice so a later re-validation does not
        silently revert to `ai.model` from config.json.
        """
        models = self.list_models()
        if model_name in models:
            self._default_model = model_name
            self._model_pinned = True
            logger.info(f"AI model set to: {model_name}")
            return True
        logger.warning(f"Model '{model_name}' not found. Available: {models}")
        return False

    def invalidate(self) -> None:
        """Forget the cached availability check so the next call re-probes.

        Used by the Components dialog's "Re-check" button and after the
        user changes `ai.model` in Settings.
        """
        self._validated = False
        self._available = None
        self._models = []
        self._model_pinned = False


# ── Module-level instance (lazy — no connection check on import) ──

ollama_ai = OllamaAIProvider()
"""Global Ollama AI provider instance. No connection check on import."""
