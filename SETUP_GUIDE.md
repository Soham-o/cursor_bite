# Cursor Bite — Setup Guide

This guide will walk you through setting up Cursor Bite from a fresh Windows machine. Every step includes **WHAT** it does, **WHY** we need it, and **WHERE** to run it.

> ## ✨ Current Status: Fully Functional & Integrated
>
> All 8 features — **Translate**, **Explain**, **Summarize**, **Search Web**, **Settings**, **Capture OCR**, **Rewrite**, and **Ask AI** — are fully integrated, wired to the global hotkey (`Ctrl+Alt+B`), and ready to use!
>
> For day-to-day shortcuts, keyboard controls, and feature examples, see **[HOW_TO_USE.md](HOW_TO_USE.md)**.
>
> The steps below guide you through installing Python dependencies and setting up the optional local engines (Ollama, Argos Translate, Tesseract OCR) at your own pace.


---

## Table of Contents

### Part 1 — Milestone 1 (required to run Cursor Bite today)

1. [Install Python](#1-install-python)
2. [Verify Python](#2-verify-python)
3. [Create a Project Folder](#3-create-a-project-folder)
4. [Create Virtual Environment](#4-create-virtual-environment)
5. [Activate Virtual Environment](#5-activate-virtual-environment)
6. [Install Python Dependencies (Milestone 1 only)](#6-install-python-dependencies-milestone-1-only)
11. [Configure Cursor Bite](#11-configure-cursor-bite)
12. [Run Cursor Bite](#12-run-cursor-bite)
13. [Test the Hotkey](#13-test-the-hotkey)

### Part 2 — Future milestones (not required yet, not wired into the app)

7. [Install Tesseract OCR — for a future OCR milestone](#7-install-tesseract-ocr--for-a-future-ocr-milestone)
8. [Install Argos Translate — for a future translation milestone](#8-install-argos-translate--for-a-future-translation-milestone)
9. [Install Ollama — for a future AI milestone](#9-install-ollama--for-a-future-ai-milestone)
10. [Download Argos Language Models — for a future translation milestone](#10-download-argos-language-models--for-a-future-translation-milestone)
14. [Translation (not yet available)](#14-translation-not-yet-available)
15. [OCR (not yet available)](#15-ocr-not-yet-available)
16. [AI (not yet available)](#16-ai-not-yet-available)

### Part 3 — Packaging & help

17. [Build a Windows EXE (Optional)](#17-build-a-windows-exe-optional)
18. [Troubleshooting](#18-troubleshooting)

---

## 1. Install Python

**WHAT:** Install Python 3.11 or newer on Windows.

**WHY:** Cursor Bite is written in Python. We need Python to run the application and install dependencies.

**WHERE:** Download from [python.org](https://www.python.org/downloads/)

**Steps:**

1. Go to [https://www.python.org/downloads/](https://www.python.org/downloads/)
2. Download the latest Python 3.11+ release (e.g., Python 3.12.x)
3. Run the installer
4. **IMPORTANT:** Check the box **"Add Python to PATH"** before clicking Install
5. Click **"Install Now"**
6. Wait for installation to complete

![Add Python to PATH](https://docs.python.org/3/_images/identity.png)

> **Note:** If you forget to check "Add Python to PATH," you can re-run the installer and choose "Modify" to add it later.

---

## 2. Verify Python

**WHAT:** Confirm Python is installed correctly and accessible from the command line.

**WHY:** We need to make sure Python and pip work before proceeding.

**WHERE:** Open **Command Prompt** (cmd) or **PowerShell**

**Command:**
```cmd
python --version
```

**Expected output:**
```
Python 3.12.x
```

**Command:**
```cmd
pip --version
```

**Expected output:**
```
pip 24.x.x from ... (python 3.12)
```

If both commands work, proceed to the next step.

---

## 3. Create a Project Folder

**WHAT:** Create a folder where Cursor Bite will live.

**WHY:** We need a dedicated directory for the project files.

**WHERE:** Your Documents folder or any location you prefer.

**Command:**
```cmd
mkdir "%USERPROFILE%\Documents\CursorBite"
cd "%USERPROFILE%\Documents\CursorBite"
```

**What this does:**
- Creates a folder called `CursorBite` in your Documents
- Changes the current directory to that folder

---

## 4. Create Virtual Environment

**WHAT:** Create an isolated Python environment for Cursor Bite.

**WHY:** A virtual environment keeps Cursor Bite's dependencies separate from other Python projects on your machine. This prevents version conflicts.

**WHERE:** Inside the CursorBite folder.

**Command:**
```cmd
python -m venv venv
```

**What this does:**
- Creates a `venv` folder containing a fresh Python installation
- This environment is independent of your system Python

---

## 5. Activate Virtual Environment

**WHAT:** Activate the virtual environment so that `pip install` puts packages inside it.

**WHY:** If you don't activate it, packages install to your system Python instead of the project.

**WHERE:** Command Prompt or PowerShell, inside the CursorBite folder.

**Command (Command Prompt):**
```cmd
venv\Scripts\activate.bat
```

**Command (PowerShell):**
```powershell
venv\Scripts\Activate.ps1
```

> **If PowerShell blocks activation:** Run this once as Administrator:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

**How you know it worked:** Your command prompt should show `(venv)` at the beginning of each line:
```
(venv) C:\Users\You\Documents\CursorBite>
```

---

## 6. Install Python Dependencies (Milestone 1 only)

**WHAT:** Install the Python packages the *current, running* app needs.

**WHY:** Milestone 1 is just the hotkey + radial menu + system tray. It uses `PyQt6` (UI) and `pywin32` (Windows hotkey/cursor APIs) — nothing else. Use `requirements-milestone1.txt`, which already exists in the repo, rather than the full `requirements.txt`.

**WHERE:** Inside the activated virtual environment, in the CursorBite folder.

**Command:**

```cmd
pip install -r requirements-milestone1.txt
```

This installs exactly:

```
PyQt6>=6.6.0
pywin32>=306
```

**What this does:**
- `PyQt6` — The UI framework for the radial menu and windows
- `pywin32` — Access to Windows APIs for global hotkeys and cursor position

**Expected output:** pip will download and install these two packages (plus PyQt6's own dependencies). This is quick.

> The full `requirements.txt` (which adds `mss`, `Pillow`, `pytesseract`,
> `argostranslate`, `pyperclip`, `requests`, `beautifulsoup4`) lists
> everything **future** milestones will need. Installing it now doesn't
> hurt, but it's not required for anything you can currently do with
> Cursor Bite — skip to [Step 11](#11-configure-cursor-bite) unless
> you're deliberately getting ahead of the next milestone.

---

## 7. Install Tesseract OCR — for a future OCR milestone

> **Not required for Milestone 1.** OCR is not wired into the running
> app yet (`infrastructure/ocr/tesseract.py` exists but nothing calls
> it from `app/controller.py`). Skip this unless you're working ahead
> on the OCR milestone.

**WHAT:** Install the Tesseract OCR engine on your system.

**WHY:** Tesseract reads text from images. Cursor Bite will use it for screen-region OCR once that milestone is implemented. pytesseract (a future dependency) is just a Python wrapper — the actual Tesseract program is separate.

**WHERE:** System-wide installation (not in the virtual environment).

**Steps:**

### Option A: Using the installer (easiest)

1. Go to [https://github.com/UB-Mannheim/tesseract/wiki](https://github.com/UB-Mannheim/tesseract/wiki)
2. Download the latest Windows installer (e.g., `tesseract-ocr-w64-setup-5.x.x.exe`)
3. Run the installer
4. **IMPORTANT:** During installation, check the box **"Additional language data"** and select any languages you need (at minimum, ensure **English** is selected)
5. Note the installation path (default: `C:\Program Files\Tesseract-OCR`)
6. Complete the installation

### Option B: Using winget (if available)

```cmd
winget install --id UB-Mannheim.TesseractOCR
```

### After installation: Tell Python where Tesseract is

Add this to your system environment variables, or create a file called `tesseract_path.txt` in the CursorBite folder containing the install path.

**To add to PATH (recommended):**

1. Press `Win + R`, type `sysdm.cpl`, press Enter
2. Go to **Advanced** tab → **Environment Variables**
3. Under **System variables**, find `Path`, click **Edit**
4. Click **New** and add: `C:\Program Files\Tesseract-OCR`
5. Click OK on all dialogs
6. **Restart your command prompt**

**Verify Tesseract is accessible:**
```cmd
tesseract --version
```

**Expected output:**
```
tesseract 5.x.x ...
```

---

## 8. Install Argos Translate — for a future translation milestone

> **Not required for Milestone 1.** Translation is not wired into the
> running app yet (`infrastructure/translation/argos.py` exists but
> nothing calls it from `app/controller.py`). Skip this unless you're
> working ahead on the translation milestone (Milestone 2).

**WHAT:** Argos Translate is an offline neural machine translation library.

**WHY:** It provides free, offline translation without any API key or internet connection. Cursor Bite will use it to translate selected text once Milestone 2 wires it in.

**WHERE:** Inside the virtual environment (it's a Python package).

**Command:**
```cmd
pip install argostranslate
```

This is **not** part of the Milestone 1 `requirements-milestone1.txt` — it's in the full `requirements.txt` for future milestones. Verify it separately:

```cmd
python -c "import argostranslate; print('Argos Translate OK')"
```

---

## 9. Install Ollama — for a future AI milestone

> **Not required for Milestone 1.** AI features (Explain, Summarize,
> Rewrite, Ask AI) are not wired into the running app yet
> (`infrastructure/ai/ollama.py` exists but nothing calls it from
> `app/controller.py`). Skip this unless you're working ahead on the
> AI milestone.

**WHAT:** Ollama is a free tool that runs large language models locally on your computer.

**WHY:** Cursor Bite will use Ollama for AI actions like Explain, Summarize, and Rewrite once that milestone is implemented.

**WHERE:** System-wide installation from [ollama.com](https://ollama.com)

**Steps:**

1. Go to [https://ollama.com](https://ollama.com)
2. Click **Download for Windows**
3. Run the installer
4. After installation, Ollama will start automatically (you'll see it in your system tray)

**Verify Ollama is running:**
```cmd
ollama list
```

**Expected output:** (may be empty if no models are downloaded yet)
```
No models available.
```

**Download a model (recommended for AI features):**

We recommend a small, fast model for desktop use. Open the command prompt and run:

```cmd
ollama pull llama3.2
```

This downloads a ~2GB model. Wait for it to complete. Other good options:
- `llama3.2` — Good balance of speed and quality (~2GB)
- `phi3.5` — Smaller, faster (~2GB)
- `tinyllama` — Very small, very fast (~600MB)

> **Note:** AI features require a model to be downloaded. The first time you use an AI action, Ollama will load the model into memory. This may take a few seconds.

---

## 10. Download Argos Language Models — for a future translation milestone

> **Not required for Milestone 1.** Only relevant once Milestone 2
> wires translation into the app.

**WHAT:** Argos Translate needs language packs to perform translations.

**WHY:** The base `argostranslate` package doesn't include translation models — you download them separately.

**WHERE:** Inside the virtual environment, via Python.

**Command:**
```cmd
python -c "import argostranslate.package; argostranslate.package.update_package_index(); print('Index updated')"
```

This updates the package index. Now install the language pairs you need.

**To install English ↔ Spanish (example):**
```cmd
python -c "import argostranslate.package; argostranslate.package.install_from_path('argostranslate/en_es')"
```

**To install all available language pairs (simple approach):**
```cmd
python -c "
import argostranslate.package
argostranslate.package.update_package_index()
available_packages = argostranslate.package.get_available_packages()
for package in available_packages:
    print(f'Installing: {package.from_code} -> {package.to_code}')
    package.install()
print('All language packs installed.')
"
```

**To check installed languages:**
```cmd
python -c "import argostranslate; print(argostranslate.translate.get_installed_languages())"
```

**Recommended minimum:** Install at least the language pairs for languages you commonly encounter. English ↔ Spanish, English ↔ French, English ↔ German, English ↔ Chinese, English ↔ Hindi are common choices.

---

## 11. Configure Cursor Bite

**WHAT:** Create the configuration file for Cursor Bite.

**WHY:** Cursor Bite needs to know things like your hotkey preference. Only the `hotkey` and `general` sections are read by the app that runs today; `translation`, `ai`, and most of `privacy` are read by `config/settings.py` but not yet acted on anywhere, since the pipeline that would use them isn't wired in yet (see the status note at the top of this guide).

**WHERE:** In the CursorBite folder.

**Steps:**

Create a file called `config.json` in the CursorBite folder:

```json
{
    "hotkey": {
        "main": "Ctrl+Alt+B"
    },
    "translation": {
        "default_target_language": "en",
        "auto_detect_source": true,
        "offline_only": false
    },
    "ai": {
        "enabled": true,
        "model": "llama3.2",
        "temperature": 0.7
    },
    "privacy": {
        "offline_mode": false,
        "no_data_retention": true,
        "clipboard_protection": true,
        "screenshot_retention": false,
        "sensitive_data_protection": true,
        "external_processing_warning": true
    },
    "ui": {
        "menu_size": 180,
        "animation_speed": 150,
        "opacity": 0.95,
        "position_behavior": "smart"
    },
    "general": {
        "start_with_windows": false,
        "enabled": true,
        "animations": true
    }
}
```

**What each section does:**

| Section | Key | Description |
|---------|-----|-------------|
| `hotkey` | `main` | The global hotkey to activate Cursor Bite |
| `translation` | `default_target_language` | Language code for translation output (en = English) |
| `translation` | `auto_detect_source` | Automatically detect the source language |
| `ai` | `enabled` | Whether AI features are enabled |
| `ai` | `model` | Ollama model name to use |
| `privacy` | `offline_mode` | When true, no external calls at all |
| `privacy` | `no_data_retention` | Don't store captured text |
| `ui` | `menu_size` | Radial menu size in pixels |
| `ui` | `opacity` | Menu transparency (0.0 to 1.0) |

---

## 12. Run Cursor Bite

**WHAT:** Start the Cursor Bite application.

**WHY:** Time to see it in action!

**WHERE:** Inside the activated virtual environment, in the CursorBite folder.

**Command:**
```cmd
python main.py
```

**Expected behavior (Milestone 1):**
1. A system tray icon appears (a small icon in your notification area near the clock)
2. The application runs in the background — no main window opens
3. Right-click the tray icon to see the menu (Settings, Privacy, About, Check Components, Exit — Settings/Privacy/Components show placeholder notifications for now)
4. Press `Ctrl + Alt + B` to activate the radial menu
5. The radial menu appears around your cursor, listing all the planned actions (Translate, Explain, Summarize, Search Web, Rewrite, Ask AI, Capture Text, Settings)
6. **Selecting any action other than Settings currently just closes the menu** — the actions themselves aren't wired to the translation/OCR/AI/search code yet
7. Press `Escape` or click outside the menu to close it

---

## 13. Test the Hotkey

**WHAT:** Verify the global hotkey works from any application.

**WHY:** The hotkey should work regardless of what application you're using.

**Steps:**

1. Open any application (Notepad, browser, etc.)
2. Select some text (highlight it with your mouse)
3. Press `Ctrl + Alt + B`
4. The Cursor Bite radial menu should appear around your cursor
5. Press `Escape` to close it

**If the hotkey doesn't work:**
- Make sure the virtual environment is activated
- Check that no other application is using `Ctrl+Alt+B`
- Try changing the hotkey in `config.json`
- Check the log file for errors

---

## 14. Translation (not yet available)

**Status:** Not wired into the running app. `infrastructure/translation/argos.py` and `app/pipeline.py` implement translation, and it's exercised in this repo's test suite, but `app/controller.py` doesn't call the pipeline yet — clicking **Translate** in the menu just closes it. This will become testable end-to-end in Milestone 2. Steps 8 and 10 above get the underlying engine ready in advance if you want to be prepared for that milestone.

---

## 15. OCR (not yet available)

**Status:** Not wired into the running app. `infrastructure/ocr/tesseract.py` implements OCR, but nothing in `app/controller.py` calls it yet — clicking **Capture Text** in the menu just closes it. Step 7 above gets the underlying engine ready in advance if you want to be prepared for that milestone.

---

## 16. AI (not yet available)

**Status:** Not wired into the running app. `infrastructure/ai/ollama.py` implements Explain/Summarize/Rewrite via Ollama, but nothing in `app/controller.py` calls it yet — clicking those actions in the menu just closes it. Step 9 above gets the underlying engine ready in advance if you want to be prepared for that milestone.

---

## 17. Build a Windows EXE (Optional)

**WHAT:** Package Cursor Bite as a standalone `.exe` file that runs without Python installed.

**WHY:** Distributing to users who don't have Python set up.

**Prerequisites:**
- PyInstaller installed: `pip install pyinstaller`
- All dependencies installed in the virtual environment

**Command:**
```cmd
pyinstaller --noconsole --onefile --name "CursorBite" --icon=assets\icons\app.ico main.py
```

**What this does:**
- `--noconsole` — Hides the console window (tray app shouldn't show a console)
- `--onefile` — Creates a single `.exe` file
- `--name "CursorBite"` — Names the output file
- `--icon` — Sets the executable icon (optional)

**Output:** The `.exe` will be in the `dist/` folder.

> **Note:** As of Milestone 1, the EXE only needs `PyQt6` and `pywin32` bundled — it doesn't do anything with Tesseract, Argos, or Ollama yet. Once translation/OCR/AI are wired in during later milestones, the EXE will additionally require Tesseract, Argos language packs, and Ollama on the target machine for those features specifically.

---

## 18. Troubleshooting

### Hotkey doesn't work
- **Problem:** The radial menu doesn't appear when pressing the hotkey.
- **Solution:**
  1. Check that the app is running (look for the tray icon)
  2. Try a different hotkey in `config.json`
  3. Make sure no other app is using the same hotkey
  4. Run from command line to see error messages: `python main.py`
  5. Check if the hotkey requires admin (it shouldn't with RegisterHotKey)

### Translate/Explain/Summarize/etc. seem to do nothing
- **This is expected in Milestone 1.** These actions aren't wired into the app yet — see the status note at the top of this guide. Selecting them just closes the menu; that's not a bug to troubleshoot.

### Translation returns an error *(only relevant once Milestone 2 wires it in)*
- **Problem:** "Translation failed" or similar error.
- **Solution:**
  1. Verify Argos language packs are installed: `python -c "import argostranslate; print(argostranslate.translate.get_installed_languages())"`
  2. Check that the source language is supported
  3. Try reinstalling argostranslate: `pip install --force-reinstall argostranslate`

### Tesseract not found *(only relevant once the OCR milestone wires it in)*
- **Problem:** "Tesseract is not installed or not in PATH"
- **Solution:**
  1. Install Tesseract (Step 7)
  2. Add Tesseract to your system PATH
  3. Restart your command prompt
  4. Verify: `tesseract --version`

### Ollama not responding *(only relevant once the AI milestone wires it in)*
- **Problem:** AI features fail with "Ollama not available"
- **Solution:**
  1. Check Ollama is running (tray icon)
  2. Run `ollama list` to verify
  3. Pull a model: `ollama pull llama3.2`
  4. Check Ollama is listening on the default port (11434)

### App doesn't start
- **Problem:** Python errors on startup.
- **Solution:**
  1. Run from command line to see the full error: `python main.py`
  2. Verify Milestone 1 dependencies are installed: `pip install -r requirements-milestone1.txt`
  3. Check Python version: `python --version` (needs 3.11+)
  4. Make sure the virtual environment is activated

### Menu appears off-screen
- **Problem:** The radial menu is partially or fully outside the visible area.
- **Solution:** This should be handled automatically by the smart positioning. If it persists, check your multi-monitor setup and screen resolution.

---

## Getting Help

If you encounter issues not covered here:

1. Check the log file (created in the CursorBite folder)
2. Run from command line to see real-time errors
3. Verify each component individually (Tesseract, Argos, Ollama)
4. Check that your system meets the requirements

---

**Congratulations!** You now have Cursor Bite installed and ready to use. Press `Ctrl+Alt+B` and experience intelligence at your cursor.
