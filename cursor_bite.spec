# Cursor Bite — PyInstaller build spec
# ============================================================
# Builds a windowed (no console) Windows executable from main.py.
#
# Only PyQt6, pywin32, and pyperclip are required for this to produce a
# working build at all — matching requirements-core.txt. Optional
# engines (argostranslate, pytesseract, mss, Pillow, ddgs,
# beautifulsoup4, requests, langdetect) are bundled automatically if
# they happen to be installed in the environment you run PyInstaller
# from, and simply skipped otherwise — the resulting EXE degrades
# exactly the way the app does when run from source: a missing engine
# disables the one action behind it, not the whole build.
#
# Usage:
#   pip install pyinstaller
#   pyinstaller cursor_bite.spec
#
# Output: dist/CursorBite/CursorBite.exe
#
# See PACKAGING.md for what is and isn't verified about this build.

import importlib.util

block_cipher = None

OPTIONAL_MODULES = [
    "argostranslate",
    "langdetect",
    "pytesseract",
    "mss",
    "PIL",
    "ddgs",
    "duckduckgo_search",
    "bs4",
    "requests",
]

hiddenimports = [m for m in OPTIONAL_MODULES if importlib.util.find_spec(m) is not None]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Cursor Bite has no ML-framework dependency of its own. These are
    # excluded defensively: if you build from a shared/system Python that
    # happens to have heavy, unrelated packages like torch installed for
    # a different project, PyInstaller's static analysis will otherwise
    # try to walk their entire submodule tree and can crash outright on
    # some torch/protobuf version combinations. Building from a clean
    # virtualenv containing only this project's own dependencies (see
    # SETUP_GUIDE.md) avoids the problem at the source; this list is the
    # fallback for when that isn't the environment you have.
    excludes=["torch", "tensorflow", "tensorboard", "jax"],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="CursorBite",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="CursorBite",
)
