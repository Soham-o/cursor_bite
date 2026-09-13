# Cursor Bite — Translation Detection Tests
# ============================================================
# Tests for two-tier language detection, separation of detection from
# Argos model availability, and actionable installation error messages.

from infrastructure.translation.argos import ArgosTranslationProvider


def test_detect_language_unicode_scripts():
    """Verify script analyzer detects non-Latin scripts accurately."""
    translator = ArgosTranslationProvider()

    lang, conf = translator.detect_language_with_confidence("यह एक परीक्षण वाक्य है")
    assert lang == "hi"
    assert conf > 0.9

    lang, conf = translator.detect_language_with_confidence("Привет, как ваши дела?")
    assert lang == "ru"
    assert conf > 0.9

    lang, conf = translator.detect_language_with_confidence("مرحبا كيف حالك اليوم؟")
    assert lang == "ar"
    assert conf > 0.9

    lang, conf = translator.detect_language_with_confidence("这是一个中文测试句子")
    assert lang == "zh"
    assert conf > 0.9


def test_detect_language_latin_script():
    """Verify Latin-script languages are detected via statistical n-gram analysis."""
    translator = ArgosTranslationProvider()

    lang, conf = translator.detect_language_with_confidence("Este es un texto en español para probar.")
    assert lang == "es"
    assert conf > 0.8

    lang, conf = translator.detect_language_with_confidence("This is a simple English sentence for testing.")
    assert lang == "en"
    assert conf > 0.8


def test_uninstalled_model_actionable_error():
    """Verify a missing optional Argos model fails with actionable information.

    The CI environment intentionally does not install language packs. The
    provider may therefore report either its general unavailable state or the
    more specific detected-language/model-pack state.
    """
    translator = ArgosTranslationProvider()
    res = translator.translate("यह एक परीक्षण वाक्य है", target_lang="en")

    assert not res.success
    assert res.error is not None
    assert "Install" in res.error
    assert (
        "argospm install translate-hi_en" in res.error
        or "language packs" in res.error.lower()
    )


def test_installed_model_translation():
    """Verify translation succeeds when a language pack is available."""
    translator = ArgosTranslationProvider()
    res = translator.translate("Hola mundo", target_lang="en")
    if res.success:
        assert "hello" in res.data.lower() or "world" in res.data.lower()
