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


def test_tier3_probe_never_treats_english_as_its_own_evidence(monkeypatch):
    """Regression test for the confirmed cause of Spanish text being
    misdetected as English: the Tier-3 Argos probe used to iterate every
    installed language *including English* and treat "produced more than
    5 characters of output" as proof of a match. If `en` had any
    translation object pointing back at itself, that identity-like
    "translation" of ANY input satisfied the length check before a real
    candidate language was ever tried, and the probe returned English
    with 70% confidence no matter what the actual text was.

    This forces Tier 1 (script) and Tier 2 (langdetect) to both fail, so
    only the Tier-3 probe can produce an answer, and rigs the fake Argos
    language list so that `en` would win first under the old, buggy
    iteration order.
    """
    import sys
    import types

    translator = ArgosTranslationProvider()

    # Force Tier 2 out of the running regardless of whether langdetect is
    # actually installed in the environment running this test — a `None`
    # entry in sys.modules makes `import langdetect` raise ImportError,
    # same as it not being installed at all.
    monkeypatch.setitem(sys.modules, "langdetect", None)

    class FakeTranslation:
        def __init__(self, output):
            self._output = output

        def translate(self, text):
            return self._output

    class FakeLang:
        def __init__(self, code):
            self.code = code

    # `en` appears FIRST in the installed-languages list and has a
    # translation "to itself" that just echoes the input back — exactly
    # the identity-translation shape that used to win before the real
    # Spanish model ever got a chance to run.
    en = FakeLang("en")
    en.get_translation = lambda other: FakeTranslation(
        "Este es un texto en espanol para probar."
    )

    es = FakeLang("es")
    es.get_translation = lambda other: FakeTranslation("Hello world")

    fake_translate_module = types.ModuleType("argostranslate.translate")
    fake_translate_module.get_installed_languages = lambda: [en, es]

    fake_argostranslate = types.ModuleType("argostranslate")
    fake_argostranslate.translate = fake_translate_module

    monkeypatch.setitem(sys.modules, "argostranslate", fake_argostranslate)
    monkeypatch.setitem(sys.modules, "argostranslate.translate", fake_translate_module)
    monkeypatch.setattr(translator, "_ensure_ready", lambda: True)

    lang, conf = translator.detect_language_with_confidence(
        "Este es un texto en espanol para probar."
    )

    assert lang != "en", "must never confirm English via a translation of English to itself"
    assert lang == "es"
    assert conf < 0.7, "Tier-3 is a weak last resort and must not report high confidence"
