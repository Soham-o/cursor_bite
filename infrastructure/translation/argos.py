# Cursor Bite — Argos Translate Provider
# ============================================================
# Uses Argos Translate for offline, free, neural machine translation.
#
# LAZY INITIALIZATION: No validation or package index update on import.
# The first call to is_available() triggers validation.
#
# IMPORTANT: Argos does NOT update its package index automatically.
# Language packs must be installed manually before use.

import logging
import re
from typing import Optional

from domain.models import TranslationResult
from infrastructure.translation.base import BaseTranslationProvider
from utils.logger import get_logger

logger = get_logger("infrastructure.translation.argos")


# ── Argos Translation Provider ─────────────────────────────────────

class ArgosTranslationProvider(BaseTranslationProvider):
    """Argos Translate implementation with lazy initialization.

    No validation is performed on __init__. The first call to
    is_available() triggers a check for installed language packs.
    """

    def __init__(self) -> None:
        self._available: Optional[bool] = None
        self._installed_languages: list[str] = []
        self._validated: bool = False

    # ── Lazy Validation ─────────────────────────────────────────

    def _ensure_ready(self) -> bool:
        """Lazy validation — called on first use."""
        if self._validated:
            return self._available or False

        self._validated = True

        try:
            import argostranslate.translate

            languages = argostranslate.translate.get_installed_languages()
            self._installed_languages = [lang.code for lang in languages]

            if self._installed_languages:
                self._available = True
                logger.info(
                    f"Argos Translate available. "
                    f"Languages: {', '.join(self._installed_languages)}"
                )
                return True
            else:
                self._available = False
                logger.info(
                    "Argos Translate is installed but no language packs found. "
                    "Install language packs to use translation."
                )
                return False
        except ImportError:
            self._available = False
            logger.info(
                "Argos Translate is not installed. "
                "Install with: pip install argostranslate"
            )
            return False
        except Exception as e:
            self._available = False
            logger.warning(f"Argos validation failed: {e}")
            return False

    # ── Language Detection & Names ──────────────────────────────

    LANGUAGE_NAMES = {
        "en": "English",
        "hi": "Hindi",
        "es": "Spanish",
        "fr": "French",
        "de": "German",
        "it": "Italian",
        "pt": "Portuguese",
        "ru": "Russian",
        "zh": "Chinese",
        "ja": "Japanese",
        "ko": "Korean",
        "ar": "Arabic",
        "el": "Greek",
        "he": "Hebrew",
        "th": "Thai",
        "sq": "Albanian",
        "nl": "Dutch",
        "pl": "Polish",
        "tr": "Turkish",
        "uk": "Ukrainian",
        "vi": "Vietnamese",
        "sv": "Swedish",
        "da": "Danish",
        "fi": "Finnish",
        "no": "Norwegian",
        "cs": "Czech",
        "ro": "Romanian",
        "hu": "Hungarian",
        "id": "Indonesian",
        "mr": "Marathi",
        "bn": "Bengali",
        "ta": "Tamil",
        "te": "Telugu",
        "ur": "Urdu",
        "fa": "Persian",
    }

    def detect_language_with_confidence(self, text: str) -> tuple[Optional[str], float]:
        """Detect the language of text with confidence score.

        Uses a two-tier approach:
        1. Fast Unicode Script Analysis (Devanagari, Cyrillic, Arabic, CJK, etc.)
           for deterministic, zero-latency detection even on single words.
        2. Statistical n-gram analysis via langdetect for Latin-based languages.
        """
        if not text or not text.strip():
            return None, 0.0

        sample = text.strip()[:1000]

        # Ignore pure punctuation/numbers
        letters = [c for c in sample if c.isalpha()]
        if not letters:
            return None, 0.0

        # Tier 1: Unicode Script Detection (high confidence on non-Latin scripts)
        script_counts = {
            "hi": len(re.findall(r"[\u0900-\u097F]", sample)),  # Devanagari
            "ru": len(re.findall(r"[\u0400-\u04FF]", sample)),  # Cyrillic
            "ar": len(re.findall(r"[\u0600-\u06FF\u0750-\u077F]", sample)),  # Arabic
            "zh": len(re.findall(r"[\u4E00-\u9FFF]", sample)),  # CJK Unified Ideographs
            "ja": len(re.findall(r"[\u3040-\u309F\u30A0-\u30FF]", sample)),  # Hiragana/Katakana
            "ko": len(re.findall(r"[\uAC00-\uD7AF\u1100-\u11FF]", sample)),  # Hangul
            "el": len(re.findall(r"[\u0370-\u03FF]", sample)),  # Greek
            "he": len(re.findall(r"[\u0590-\u05FF]", sample)),  # Hebrew
            "th": len(re.findall(r"[\u0E00-\u0E7F]", sample)),  # Thai
        }

        total_letters = len(letters)
        for code, count in script_counts.items():
            if count > 0 and (count / total_letters) >= 0.25:
                # Script strongly matched
                confidence = min(0.99, round(0.85 + (count / total_letters) * 0.14, 2))
                return code, confidence

        # Tier 2: Statistical Language Detection (langdetect)
        try:
            import langdetect
            langs = langdetect.detect_langs(sample)
            if langs:
                top = langs[0]
                return top.lang, round(top.prob, 2)
        except Exception:
            pass

        # Tier 3: Installed Argos language probe fallback.
        #
        # BUG FIXED: this used to iterate every installed language
        # *including English itself* and treat "the model produced more
        # than 5 characters of output" as proof of a source-language
        # match. Two problems: (a) an NMT model doesn't refuse
        # out-of-domain input, so almost any installed X->en model
        # produces *some* plausible-looking output for *any* input,
        # making ">5 chars" no signal at all; (b) English was never
        # excluded, so if `en` happened to have a translation object
        # pointing at itself (some argostranslate builds resolve a
        # same-language pair to an identity translation), that identity
        # "translation" of e.g. Spanish text back to itself would satisfy
        # the length check first and confidently report English. That
        # was the confirmed cause of Spanish text being misdetected as
        # English when the langdetect package (Tier 2) was unavailable.
        #
        # This is inherently a weak last resort — it can only ever
        # confirm "some installed model round-trips this text", not
        # identify the language — so it is scored low (0.55) and must
        # never be treated as equivalent to a real detector's confidence.
        #
        # PERFORMANCE FIX: each candidate requires argostranslate to load
        # a real NMT model from disk on first use and run actual
        # inference — measured at several seconds *per language* the
        # first time. The original loop tried every installed language,
        # which reproduced as a genuine ~14-20 second stall (confirmed
        # live and by direct timing) on a translate action that was
        # ultimately only guessing. Capped to a handful of candidates so
        # the worst case (langdetect unavailable, text this ambiguous)
        # is bounded rather than scaling with how many language packs
        # happen to be installed.
        _MAX_TIER3_CANDIDATES = 2
        if self._ensure_ready():
            try:
                import argostranslate.translate
                languages = argostranslate.translate.get_installed_languages()
                en_obj = next((lang_obj for lang_obj in languages if lang_obj.code == "en"), None)
                if en_obj:
                    tried = 0
                    for lang in languages:
                        if lang.code == "en":
                            # Translating English "through itself" proves
                            # nothing about the source language and must
                            # never be used as a detection signal.
                            continue
                        if tried >= _MAX_TIER3_CANDIDATES:
                            break
                        tried += 1
                        try:
                            tr = lang.get_translation(en_obj)
                            if tr:
                                res = tr.translate(sample[:200])
                                if res and len(res) > 5:
                                    return lang.code, 0.55
                        except Exception:
                            continue
            except Exception:
                pass

        # No script match, no statistical detector available, and no
        # installed-model probe succeeded — this is genuinely ambiguous
        # Latin-script text. Reporting "en" here would be a confident
        # guess with zero evidence behind it, so report unknown instead
        # and let the caller ask the user to pick a source language.
        return None, 0.0

    def detect_language(self, text: str) -> Optional[str]:
        """Detect the language code (ISO 639-1) of the text."""
        lang, _ = self.detect_language_with_confidence(text)
        return lang

    # ── Interface Implementation ────────────────────────────────

    def name(self) -> str:
        return "Argos Translate (Offline)"

    def is_available(self) -> bool:
        return self._ensure_ready()

    def translate(
        self,
        text: str,
        source_lang: Optional[str] = None,
        target_lang: str = "en",
    ) -> TranslationResult:
        """Translate text with independent language detection and clear error states."""
        if not self._ensure_ready():
            return TranslationResult(
                success=False,
                error="Argos Translate is not available. Install language packs to use translation.",
                original_text=text,
                target_language=target_lang,
            )

        if not text or not text.strip():
            return TranslationResult(
                success=False,
                error="No text provided for translation.",
                original_text=text,
                target_language=target_lang,
            )

        # Limit text length for safety
        max_length = 5000
        if len(text) > max_length:
            text = text[:max_length]

        try:
            import argostranslate.translate

            languages = argostranslate.translate.get_installed_languages()

            # Step 1: Determine source language and confidence
            from_lang = source_lang
            confidence = 1.0

            if from_lang is None:
                detected_code, detected_conf = self.detect_language_with_confidence(text)
                from_lang = detected_code
                confidence = detected_conf

            target_name = self.LANGUAGE_NAMES.get(target_lang, target_lang.upper())

            if from_lang is None:
                return TranslationResult(
                    success=False,
                    error=(
                        "Could not determine source language. "
                        "Please select more text or choose a source language in Settings."
                    ),
                    original_text=text,
                    target_language=target_lang,
                )

            source_name = self.LANGUAGE_NAMES.get(from_lang, from_lang.upper())
            conf_pct = int(confidence * 100)

            # Step 2: Check if already in target language
            if from_lang == target_lang:
                return TranslationResult(
                    success=True,
                    data=text,
                    source_language=from_lang,
                    target_language=target_lang,
                    original_text=text,
                    metadata={
                        "untranslated": True,
                        "confidence": confidence,
                        "source_name": source_name,
                        "target_name": target_name,
                        "note": f"Selected text is already in {target_name} ({conf_pct}% confidence).",
                    },
                )

            # Step 3: Check Argos installed models
            source_obj = next((lang_obj for lang_obj in languages if lang_obj.code == from_lang), None)
            target_obj = next((lang_obj for lang_obj in languages if lang_obj.code == target_lang), None)

            if source_obj is None:
                return TranslationResult(
                    success=False,
                    error=(
                        f"{source_name} detected ({conf_pct}% confidence), but the "
                        f"{source_name} → {target_name} translation pack is not installed.\n\n"
                        f"Install the required Argos language pack from Settings or run:\n"
                        f"  argospm install translate-{from_lang}_{target_lang}"
                    ),
                    original_text=text,
                    target_language=target_lang,
                    source_language=from_lang,
                    metadata={"confidence": confidence, "detected": from_lang},
                )

            if target_obj is None:
                return TranslationResult(
                    success=False,
                    error=(
                        f"Target language '{target_name}' is not installed in Argos Translate.\n\n"
                        f"Install the language pack via:\n"
                        f"  argospm install translate-{from_lang}_{target_lang}"
                    ),
                    original_text=text,
                    target_language=target_lang,
                    source_language=from_lang,
                )

            # Step 4: Check translation pair
            translation = source_obj.get_translation(target_obj)
            if translation is None:
                return TranslationResult(
                    success=False,
                    error=(
                        f"{source_name} is installed, but no translation pair from "
                        f"{source_name} to {target_name} is available.\n\n"
                        f"Install it via:\n"
                        f"  argospm install translate-{from_lang}_{target_lang}"
                    ),
                    original_text=text,
                    target_language=target_lang,
                    source_language=from_lang,
                    metadata={"confidence": confidence},
                )

            # Step 5: Execute translation
            result_text = translation.translate(text)
            logger.info(f"Translation completed: {from_lang} ({source_name}) to {target_lang} ({target_name}).")

            return TranslationResult(
                success=True,
                data=result_text,
                source_language=from_lang,
                target_language=target_lang,
                original_text=text,
                metadata={
                    "confidence": confidence,
                    "source_name": source_name,
                    "target_name": target_name,
                },
            )

        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return TranslationResult(
                success=False,
                error=f"Translation failed: {str(e)}",
                original_text=text,
                target_language=target_lang,
                source_language=source_lang,
            )

    def supported_languages(self) -> list[str]:
        """List of language codes this provider supports."""
        if self._installed_languages:
            return self._installed_languages
        return []

    # ── Re-validation ───────────────────────────────────────────

    def invalidate(self) -> None:
        """Forget the cached availability check so the next call re-probes.

        Used by the Components dialog's "Re-check" button so a user who
        installs language packs while Cursor Bite is running does not have
        to restart the app.
        """
        self._validated = False
        self._available = None
        self._installed_languages = []


# ── Module-level instance (lazy — no validation on import) ────────

argos_translator = ArgosTranslationProvider()
"""Global Argos Translate provider instance. No validation on import."""
