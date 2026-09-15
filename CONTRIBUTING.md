# Contributing to Cursor Bite

Thanks for considering a contribution. This project is small on purpose —
see the "important product principle" in README.md before proposing a big
new feature: does it improve context, intelligence, speed, privacy, or
reliability? If not, it probably doesn't belong.

## Development setup

See [SETUP_GUIDE.md](SETUP_GUIDE.md) for a full fresh-machine walkthrough.
Short version:

```cmd
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install pytest ruff
python -m pytest tests/ -q
```

## Before opening a PR

1. **Run the tests.** `python -m pytest tests/ -q` — the suite runs headless,
   with no display, network, Ollama, Tesseract, or Argos packs required.
   Every test should pass; a PR that leaves a test failing won't be merged.
2. **Run the linter.** `ruff check .`
3. **Trace what you changed**, not just what you added. If you touch the
   privacy gateway, the pipeline, or anything that reads the clipboard or
   selection, re-read the relevant section of README.md's Privacy Model
   first — those invariants (local-first, no unnecessary retention, no
   content in logs) are the parts of this project that matter most.
4. **No new mandatory paid dependency.** Cursor Bite has zero mandatory
   cost by design — no required API key, no required cloud service. Optional
   local/free engines behind an optional action are fine (that's the whole
   architecture); anything that would break "the app still works with none
   of the optional components installed" is not.

## Code conventions

- Ports-and-adapters layering: `domain/` defines interfaces and pure data,
  `infrastructure/` implements them, `app/` orchestrates, `ui/` presents.
  `domain/` must never import from `infrastructure/` or `ui/`.
- Every optional provider (translation, OCR, AI, search) is lazily
  resolved and fails safe — importing the module or constructing the
  provider must never raise; unavailability is reported through
  `is_available()` / an `unavailable_hint`, not an exception that reaches
  the UI. See `app/pipeline.py`'s `_load()` for the existing pattern.
- **Never log user content.** Not selected text, not prompts, not
  translations, not search queries, not screenshots. Log action names,
  durations, exception *types*, and outcomes — see the module docstrings in
  `app/pipeline.py` and `app/controller.py` for the existing convention.
- Nothing may block the Qt UI thread. Anything that can take non-trivial
  time (clipboard polling, network calls, model inference, subprocess
  calls) goes through `utils/threading.run_async`.
- Type hints on new public functions; small, single-purpose functions over
  large ones; prefer extending an existing provider/pattern over inventing
  a parallel one.

## Testing conventions

- Tests must not touch the real desktop: no real Ctrl+C, no real clipboard,
  no real network call, no real Ollama/Tesseract/Argos dependency. Use the
  fakes and fixtures already in `tests/conftest.py` and the existing test
  files as a template — in particular, the `no_real_keystrokes` autouse
  fixture exists because a mistake here really did type into a
  contributor's editor once.
- Don't add a test solely to inflate the count. Test the actual failure
  mode: what real input, state, or missing dependency should produce what
  observable behavior.

## Reporting bugs / requesting features

Use the issue templates. For anything security-relevant, see
[SECURITY.md](SECURITY.md) instead of a public issue.

## License

By contributing, you agree your contribution is licensed under this
project's [MIT License](LICENSE).
