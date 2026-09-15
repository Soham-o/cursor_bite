# Packaging Cursor Bite as a Windows Executable

## Quick start

```cmd
pip install pyinstaller
pyinstaller cursor_bite.spec
```

Output: `dist/CursorBite/CursorBite.exe` — a folder distribution (not a
single-file EXE). Copy the whole `dist/CursorBite/` folder to distribute it;
everything the app needs at runtime lives alongside the `.exe`.

**Build from a clean virtual environment** containing only this project's
own dependencies (`requirements-core.txt` or `requirements.txt`), not a
shared system Python with unrelated packages installed. PyInstaller's static
analysis walks the entire import graph it can see — an unrelated heavy
package like PyTorch sitting in the same environment for a different project
can make analysis dramatically slower, or in some version combinations,
crash outright. `cursor_bite.spec` excludes a few common offenders (`torch`,
`tensorflow`, `tensorboard`, `jax`) as a safety net, but a clean venv is the
actual fix.

## What gets bundled

`cursor_bite.spec` always bundles `PyQt6` and `pywin32` (Cursor Bite's hard
requirements). It also auto-detects and bundles whichever of these are
installed in the environment you run PyInstaller from, and skips the rest:

| Package | Powers |
|---|---|
| `argostranslate`, `langdetect` | Translate |
| `pytesseract`, `mss`, `Pillow` | Capture OCR |
| `requests`, `beautifulsoup4`, `ddgs` | Search Web |

**The resulting EXE degrades exactly like the app run from source.** If you
build without `pytesseract` installed, the EXE still runs and every other
action still works — Capture Text just reports what to install, the same
message you'd see running `python main.py` in that state.

**Argos language packs, the Tesseract engine itself, and Ollama are never
bundled** — they're external programs / downloaded model files, not Python
packages PyInstaller can embed. A machine running the EXE still needs them
installed separately for the corresponding actions, exactly as documented in
SETUP_GUIDE.md.

## What is and isn't verified

**VERIFIED** on this Windows machine, in this pass:
- `pyinstaller cursor_bite.spec` completes and produces `dist/CursorBite/CursorBite.exe`.

**NOT independently runtime-verified in this pass:**
- Launching `dist/CursorBite/CursorBite.exe` itself, interacting with the
  tray icon, and exercising the hotkey/menu/actions from the packaged build
  specifically (as opposed to `python main.py`, which *was* run and
  exercised live — see the completion report). A packaged build pulls in a
  different set of bundled DLLs and can occasionally hit issues `python
  main.py` doesn't (a missing Qt plugin, a `pywin32` DLL not found at the
  path PyInstaller placed it). Do this once before cutting a release:

```cmd
cd dist\CursorBite
CursorBite.exe
```

Confirm the tray icon appears, the hotkey opens the radial menu, and at
least one action (e.g. Translate, if you have a language pack installed)
produces a real result.

## Building a single-file EXE instead

The default spec produces a folder (`COLLECT`), which starts faster and is
more reliable for PyQt6 apps than a single-file build. If you specifically
want one file, change the `EXE(...)` block in `cursor_bite.spec` to include
`a.binaries, a.zipfiles, a.datas,` in its own argument list and set
`exclude_binaries=False`, and remove the trailing `COLLECT(...)` block — or
build directly from the command line instead of the spec:

```cmd
pyinstaller --noconsole --onefile --name CursorBite main.py
```

Single-file builds unpack themselves to a temp directory on every launch,
which adds a startup delay proportional to the bundle size — noticeable
enough that the folder build is the documented default here.

## Installer

No installer (MSI/NSIS/Inno Setup) is included yet. Packaging is currently
"build an EXE, copy the folder" — see the Roadmap in README.md.
