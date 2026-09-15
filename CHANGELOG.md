# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Fixed

- **UI-thread blocking on every hotkey press.** Selection capture (a
  simulated Ctrl+C plus a clipboard poll that can take up to ~500ms) used
  to run synchronously in `Controller.on_hotkey()`, freezing the radial menu
  before it could even appear. It now runs off the UI thread after the menu
  is already visible, with a generation counter so a stale or superseded
  capture can never overwrite a newer one or leak into the next session.
- **Spanish (and other Latin-script) text misdetected as English during
  translation** when the `langdetect` package was unavailable. The
  language-detection fallback tier iterated every installed Argos language
  *including English itself* and treated "produced more than 5 characters
  of output" as proof of a match — an identity-like English→English
  translation object satisfied that check before a real candidate language
  ever got a chance. English is now excluded from that probe, and its
  confidence score was lowered to reflect that it's a last-resort guess,
  never a substitute for a real detector.
- **Capture Text (OCR) crashed with an unhandled `ModuleNotFoundError`**
  instead of degrading gracefully when the `mss` screen-capture package was
  missing while Tesseract itself was present. Found live during a smoke
  test of this release. Capture readiness now checks both dependencies
  before opening the region selector, and the capture path itself degrades
  to an actionable message instead of an unhandled worker error if the
  package goes missing anyway.
- A `QObject` (the application event bus) constructed during pytest's
  module-collection phase, before any `QApplication` existed yet, could
  later be invalidated by PyQt once a test's own `qapp` fixture created
  one — surfacing as `RuntimeError: wrapped C/C++ object ... has been
  deleted`. `tests/conftest.py` now creates the `QApplication` at
  conftest-import time, before any test module is collected.

### Removed

- `domain/services.py` — an entire unused orchestration layer
  (`TranslationService`, `OCRService`, `AIService`, `SearchService`,
  `ClipboardService`) that duplicated logic already implemented directly in
  `app/pipeline.py`. Confirmed dead via repo-wide search before deletion:
  nothing imported it.

### Changed

- Relocated the browser-based UI/UX design prototype (`web/`, `server.js`,
  `package.json`) to `design/web-prototype/`, with a new README explaining
  what it is and that it has no runtime connection to the actual Windows
  application. It previously sat at the repository root with no
  explanation, indistinguishable from a second, half-finished product.
- Hardened `design/web-prototype/server.js`: the static file server's
  directory-traversal check was a plain string-prefix comparison
  (`filePath.startsWith(WEB_DIR)`), bypassable by a sibling directory
  sharing the prefix; it now resolves the real path and checks a proper
  path-separator boundary. Its CORS header was a blanket
  `Access-Control-Allow-Origin: *` on a server that proxies to local Ollama
  with no authentication; it now reflects only `localhost`/`127.0.0.1`
  origins.
- Rewrote SETUP_GUIDE.md, which described the app as "Milestone 1 only"
  with Translate/Explain/Summarize/Rewrite/Ask AI/OCR/Search "not wired
  in" — false as of this codebase; all of those are implemented and
  wired end-to-end. It also referenced a `requirements-milestone1.txt`
  that does not exist (the real file is `requirements-core.txt`).
- Removed stale "Milestone 1" framing from `infrastructure/storage/database.py`'s
  docstring.

### Added

- Test coverage for the two P0 fixes above (selection-capture generation
  state machine, the Argos Tier-3 detection bug), plus previously-untested
  pure logic: the hotkey string parser (`parse_hotkey`) and multi-monitor
  cursor geometry (`get_virtual_screen_bounds`, `is_cursor_near_edge`).
- `cursor_bite.spec` (PyInstaller build spec) and `PACKAGING.md`.
- `SECURITY.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, this changelog,
  and `.github/` (CI workflow, issue templates, PR template).

## [0.1.0] — repository baseline

The state of the project before this pass: hexagonal architecture with a
working hotkey → radial menu → two-phase pipeline → result-panel flow;
real (not stubbed) translation (Argos), local AI (Ollama), OCR (Tesseract),
and web search (DuckDuckGo) providers; a privacy gateway distinguishing
local-vs-external processing with consent flow; 266 passing tests. Not
tagged as a release at the time.
