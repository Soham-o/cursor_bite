# Cursor Bite — Setup Guide

This guide walks you through setting up Cursor Bite on a fresh Windows machine.
Every step says **WHAT** it does, **WHY** you need it, and **WHERE** to run it.

> ## Current status: core experience works end-to-end today
>
> The hotkey, radial menu, tray, privacy gateway, offline translation, local
> AI (Explain/Summarize/Rewrite/Ask AI), screen-region OCR, and web search are
> all wired up and usable right now — not placeholders. Each one is optional:
> install only the engines behind the actions you want, and everything else
> keeps working. See [README.md](README.md) for the full feature list and
> what's still experimental.

---

## Table of Contents

### Part 1 — Get the app running (required)

1. [Install Python](#1-install-python)
2. [Verify Python](#2-verify-python)
3. [Get the code](#3-get-the-code)
4. [Create a virtual environment](#4-create-a-virtual-environment)
5. [Activate the virtual environment](#5-activate-the-virtual-environment)
6. [Install the core dependencies](#6-install-the-core-dependencies)
7. [Configure Cursor Bite](#7-configure-cursor-bite)
8. [Run Cursor Bite](#8-run-cursor-bite)
9. [Test the hotkey](#9-test-the-hotkey)

### Part 2 — Optional engines (install only what you want)

10. [Offline Translation — Argos Translate](#10-offline-translation--argos-translate)
11. [Local AI — Ollama](#11-local-ai--ollama)
12. [Screen-Region OCR — Tesseract](#12-screen-region-ocr--tesseract)
13. [Web Search](#13-web-search)

### Part 3 — Packaging & help

14. [Building a Windows EXE](#14-building-a-windows-exe)
15. [Troubleshooting](#15-troubleshooting)

---

## 1. Install Python

**WHAT:** Install Python 3.11 or newer on Windows.

**WHY:** Cursor Bite is written in Python.

**WHERE:** [python.org/downloads](https://www.python.org/downloads/)

1. Download the latest Python 3.11+ release.
2. Run the installer.
3. **Check "Add Python to PATH"** before clicking Install.
4. Click **Install Now**.

## 2. Verify Python

```cmd
python --version
pip --version
```

Both should print a version number. If not, re-run the installer and choose
"Modify" to add Python to PATH.

## 3. Get the code

```cmd
git clone https://github.com/<your-fork-or-org>/cursor_bite.git
cd cursor_bite
```

(Or download and extract the ZIP from GitHub, then `cd` into the folder.)

## 4. Create a virtual environment

**WHY:** Keeps Cursor Bite's dependencies separate from other Python projects.

```cmd
python -m venv venv
```

## 5. Activate the virtual environment

```cmd
:: Command Prompt
venv\Scripts\activate.bat

:: PowerShell
venv\Scripts\Activate.ps1
```

> If PowerShell refuses to run the script, run this once as Administrator:
> `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

You'll know it worked when the prompt shows `(venv)` at the start of the line.

## 6. Install the core dependencies

**WHAT:** The smallest install that gives you a fully working app: the
hotkey, the radial menu, the tray, safe text capture, and the result panel.

```cmd
pip install -r requirements-core.txt
```

This installs exactly `PyQt6`, `pywin32`, and `pyperclip`. Every action still
appears in the menu at this point — Translate/Explain/Summarize/etc. will
just tell you what to install if you try them before their engine is set up
(Part 2 below).

For everything at once instead of installing engines one at a time:

```cmd
pip install -r requirements.txt
```

## 7. Configure Cursor Bite

**WHAT:** `config.json` in the project root controls the hotkey, target
translation language, AI model, and privacy settings.

**WHY:** A default `config.json` ships in the repo already — you only need to
edit it to change something (e.g. pick a different hotkey or target language).

A minimal example:

```json
{
    "hotkey": { "main": "Ctrl+Alt+B" },
    "translation": { "default_target_language": "en", "auto_detect_source": true },
    "ai": { "enabled": true, "model": "llama3.2", "temperature": 0.7 },
    "privacy": { "offline_mode": false, "sensitive_data_protection": true },
    "general": { "enabled": true }
}
```

Every field is read by the running app — see `config/defaults.py` for the
full list with descriptions.

## 8. Run Cursor Bite

```cmd
python main.py
```

**What happens:**

1. A system tray icon appears (look for the dark "CB" icon near the clock).
2. No window opens — this is a background/tray app.
3. Right-click the tray icon for **Settings**, **Privacy**, **Check
   Components**, **Offline Mode**, **About**, and **Exit** — all of these are
   real, working windows, not placeholders.
4. Press `Ctrl+Alt+B` to open the radial menu at your cursor.

## 9. Test the hotkey

1. Open any application (Notepad, a browser, an editor).
2. Select some text.
3. Press `Ctrl+Alt+B` — the radial menu should appear at your cursor
   immediately.
4. Press `1` for **Translate**. If you haven't installed a language pack yet
   (Part 2), you'll get a message telling you exactly what to run — that's
   expected, not a bug.
5. Press `Escape` to close the menu.

If the hotkey doesn't respond, see [Troubleshooting](#15-troubleshooting).

---

## 10. Offline Translation — Argos Translate

**WHAT:** Argos Translate is a free, fully offline neural machine translation
library — no API key, no internet connection needed once packs are
installed.

```cmd
pip install argostranslate langdetect
```

Then install the language pairs you actually want (this reaches out to
Argos's package index once, to download the model files — after that,
translation itself is 100% offline):

```cmd
python -c "import argostranslate.package; argostranslate.package.update_package_index()"
python -c "
import argostranslate.package
for pkg in argostranslate.package.get_available_packages():
    if pkg.from_code in ('es', 'fr', 'de', 'hi') and pkg.to_code == 'en':
        pkg.install()
"
```

Adjust the `from_code` list to the languages you expect to translate *from*.
`to_code` is whatever you set as `translation.default_target_language` in
`config.json` (default: `en`).

**Verify:**

```cmd
python -c "import argostranslate.translate; print(argostranslate.translate.get_installed_languages())"
```

## 11. Local AI — Ollama

**WHAT:** Ollama runs open-weight language models entirely on your machine.
Powers **Explain**, **Summarize**, **Rewrite**, and **Ask AI**.

1. Download and install from [ollama.com](https://ollama.com).
2. Ollama starts automatically after install (tray icon near the clock).
3. Pull a small, fast model:

```cmd
ollama pull llama3.2
```

Other options: `phi3.5` (smaller/faster), `tinyllama` (very small),
`mistral`, `qwen2.5`. Set your choice as `ai.model` in `config.json`.

**Verify:**

```cmd
ollama list
```

If Ollama is running but no model matches `ai.model`, Cursor Bite falls back
to the first installed model and logs which one it picked.

## 12. Screen-Region OCR — Tesseract

**WHAT:** Tesseract reads text out of anything you can see but can't select —
images, video, locked PDFs, canvas-based apps.

Two things are needed: the Tesseract engine itself, and two Python packages
that talk to it and grab the screen pixels.

```cmd
pip install pytesseract mss Pillow
```

Then install the engine:

- **Installer (recommended):** download from
  [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki) and
  run it. Default path: `C:\Program Files\Tesseract-OCR`.
- **winget:** `winget install --id UB-Mannheim.TesseractOCR`

Add `C:\Program Files\Tesseract-OCR` to your `PATH` (Environment Variables →
System variables → `Path` → New), then restart your terminal.

**Verify:**

```cmd
tesseract --version
```

Use **Capture OCR** from the radial menu (`6`), then drag a box over any text
on screen.

## 13. Web Search

**WHAT:** DuckDuckGo search results, shown in the result panel. This is the
**one** action that sends anything off your device — the privacy gateway
warns you before it does, unless you've turned that warning off.

```cmd
pip install requests beautifulsoup4 ddgs
```

No API key, no account. It's a best-effort feature: DuckDuckGo's HTML
endpoint occasionally rate-limits or shows a bot-check page, in which case
Cursor Bite reports that plainly rather than pretending the search worked.

---

## 14. Building a Windows EXE

**WHAT:** Package Cursor Bite as a standalone `.exe` so it runs without a
Python install.

```cmd
pip install pyinstaller
pyinstaller cursor_bite.spec
```

A `cursor_bite.spec` is included in the repo root — see
[PACKAGING.md](PACKAGING.md) for what it bundles and its current
limitations. The output lands in `dist/CursorBite/`.

Optional engines (Tesseract, Ollama, Argos language packs) are **not**
bundled into the EXE — they still need to be installed on the machine that
runs it, same as with the Python version.

---

## 15. Troubleshooting

### The hotkey doesn't open the menu

- Confirm Cursor Bite is running (look for the tray icon).
- Confirm "Enabled" is checked in the tray menu.
- Another app may already be using `Ctrl+Alt+B` — change the hotkey in
  **Settings**, or edit `hotkey.main` in `config.json`.
- Run `python main.py` from a terminal to see errors directly.

### An action's result says a component isn't available

This is the intended behavior, not a bug — every optional engine reports
exactly what's missing and how to install it. Open **Check Components**
from the tray menu to see the status of every engine at once, and use its
**Re-check** button after installing something instead of restarting the app.

### Translation fails with an error

- Verify installed languages: `python -c "import argostranslate.translate; print(argostranslate.translate.get_installed_languages())"`
- Make sure a pack exists for your *specific* source → target pair — having
  Spanish and English installed doesn't give you French → English.

### "AI is not available"

- Confirm Ollama is running: `ollama list`
- Confirm the model in `config.json` (`ai.model`) is actually pulled:
  `ollama pull llama3.2`

### "Screen capture needs the 'mss' package" / OCR errors

- `pip install mss Pillow pytesseract`
- Confirm `tesseract --version` works from the same terminal you're running
  Cursor Bite from (a PATH change needs a fresh terminal to take effect).

### The radial menu appears off-screen or clipped

Should not happen — the menu clamps itself inside the screen bounds on every
monitor, including near corners and taskbars. If you see this, please file
an issue with your monitor layout and scaling percentage.

### App doesn't start at all

1. Run `python main.py` from a terminal and read the actual error.
2. Confirm dependencies: `pip install -r requirements-core.txt`
3. Confirm Python version: `python --version` (needs 3.11+)
4. Confirm the virtual environment is activated (`(venv)` in the prompt).

---

## Getting help

1. Check `%USERPROFILE%\.cursor_bite\cursor_bite.log` for the technical log
   (it never contains your selected text, prompts, or search queries — see
   the Privacy Model in [README.md](README.md)).
2. Open **Check Components** from the tray to see engine status at a glance.
3. If something looks wrong, open an issue — see [CONTRIBUTING.md](CONTRIBUTING.md).

*Press `Ctrl+Alt+B` and go.*
