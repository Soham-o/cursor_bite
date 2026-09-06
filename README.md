# Cursor Bite

**Intelligence at your cursor.**

A privacy-first, local-first Windows AI assistant that appears around your mouse cursor when activated through a customizable global hotkey.

## What is Cursor Bite?

Cursor Bite is a contextual AI assistant for Windows that stays out of your way until you need it. Select some text anywhere — a browser, a PDF, an IDE, a chat window — press `Ctrl+Alt+B`, and a radial menu appears around your cursor. Pick an action and the answer opens next to where you were already looking.

No window to switch to, no tab to paste into, no account to sign into.

## Features

- **Global Hotkey** — Activate with a customizable key combination (`Ctrl+Alt+B` by default) from any application, via native `RegisterHotKey`/`WM_HOTKEY`
- **Cursor-Positioned Radial Menu** — Appears around your mouse, repositions near screen edges, multi-monitor and DPI aware; Escape or an outside click dismisses it
- **Safe Text Capture** — Reads your selection by taking a snapshot of the clipboard, copying, and putting the original back, so using Cursor Bite never costs you what you had copied
- **Universal Translation** — Fully offline neural translation via Argos Translate, into whichever language you configure
- **Explain, Summarize, Rewrite, Ask AI** — Local AI through Ollama; the model runs on your machine and the text never leaves it
- **OCR** — Drag a region of the screen and get its text, via Tesseract. Works on anything you can see: images, screenshots, video, applications that refuse to let you select text
- **Web Search** — DuckDuckGo results in the result panel; the one action that sends anything off-device, and it says so before it does
- **Result Panel** — Opens near the cursor, scrolls, copies to clipboard, and closes on Escape
- **Privacy Gateway** — Pattern-based detection of emails, phone numbers, API keys, credit cards (Luhn-validated), tokens and private IPs, feeding a policy engine that decides local-vs-external per action, blocks what shouldn't leave, and asks before anything does
- **System Tray** — Runs quietly in the tray, with real Settings, Privacy and Check Components windows
- **Graceful degradation** — Every optional component is genuinely optional. Missing Tesseract, Ollama, Argos packs or an internet connection disables exactly one action and reports what to install; a fresh install with none of them present still starts and runs

At startup, Cursor Bite performs zero network requests and initializes zero optional components. Nothing is imported, probed or connected to until an action needs it.

## Architecture

```
User presses hotkey
        │
        ▼
  Hotkey Listener (RegisterHotKey)
        │
        ▼
  Cursor Detection (cursor position)
        │
        ▼
  Radial Menu (PyQt6 overlay)
        │
        ▼
  User selects action
        │
        ▼
  Context Pipeline
  ┌──────────────────┐
  │ Context Provider │  ← selected text / clipboard / screen region / OCR
  ├──────────────────┤
  │ Privacy Gateway  │  ← detect sensitive data, decide local vs external
  ├──────────────────┤     (may pause here for explicit consent)
  │ Translation      │  ← Argos Translate (offline)
  │ OCR              │  ← Tesseract (offline)
  │ AI               │  ← Ollama (local)
  │ Search           │  ← DuckDuckGo (free, best-effort)
  ├──────────────────┤
  │ Result Display   │  ← near cursor
  └──────────────────┘
```

Layers depend inwards only: `ui/` and `app/` know about `domain/` interfaces, `infrastructure/` implements them, and `domain/` knows about nothing else. Providers are resolved lazily and failure-safely, which is what makes the startup guarantee and the degradation guarantee above hold.

The pipeline runs in two phases — `prepare()` extracts and decides, `execute()` does the work — so the consent dialog has a seam to sit in: it runs on the UI thread between them, with the work either side of it on a worker thread. If you decline, nothing had run yet, so nothing was sent.

## Privacy Philosophy

- **Local first** — Everything that can be processed locally is processed locally. Translation, OCR and AI are all local; search is the only action that leaves the machine
- **No persistent storage** of captured text, screenshots, or clipboard history by default
- **Sensitive data never leaves the device unintentionally** — detected patterns never block *local* processing, because the text is already on your machine and blocking it would only make the app useless for the documents you most want help with. They do block — or require explicit consent for — anything that would send them to an external service
- **Your clipboard is yours** — it is snapshotted and restored on every path, including the ones where the capture failed
- **No telemetry** — no analytics, no tracking, no hidden data collection
- **No keylogging** — we never monitor your keystrokes
- **No screen recording** — we only capture when you explicitly activate
- **No user content in the logs** — logs carry action names, durations and error types, never the text you processed

## Technology

- **Python 3.11+**
- **PyQt6** — UI framework
- **pywin32** — Windows API integration (hotkeys, clipboard)
- **mss** + **Pillow** — Screen capture
- **Tesseract** — OCR engine
- **Argos Translate** — Offline neural machine translation
- **Ollama** — Local AI runtime
- **DuckDuckGo** — Web search, via its HTML endpoint (no API key)

## How to Use

See **[HOW_TO_USE.md](HOW_TO_USE.md)** for the complete guide, keyboard shortcut reference (`1`–`8`), feature walkthroughs, and tray operations.

**Quick Summary:**
1. Start the app: `python main.py` (or `.\venv\Scripts\python.exe main.py`)
2. Select text anywhere on your screen
3. Press `Ctrl+Alt+B` to open the radial HUD at your cursor
4. Press keys `1`–`8` or click any sector:
   - `[1]` Translate (Offline)
   - `[2]` Summarize (AI)
   - `[3]` Explain (AI)
   - `[4]` Search Web (DuckDuckGo)
   - `[5]` Settings
   - `[6]` Capture OCR (Screen sniper)
   - `[7]` Rewrite (AI)
   - `[8]` Ask AI (Freeform or contextual)

## Tests

```bash
python -m pytest tests/ -q
```

238 tests covering the privacy detector and gateway, every pipeline action, the clipboard save/restore invariant, the search rate limiter, graceful degradation when packages are missing, the two-phase consent seam, and modern radial HUD keyboard & mouse navigation. They need no display, no network, no Ollama, no Tesseract and no Argos packs.

## Setup

See [SETUP_GUIDE.md](SETUP_GUIDE.md) — it covers the minimum needed to launch, then each optional component separately, so you can install only the ones whose actions you want.

## License

MIT License — see [LICENSE](LICENSE) for details.

