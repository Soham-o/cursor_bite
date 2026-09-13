# Contributing to Cursor Bite

Thank you for your interest in Cursor Bite.

## Development principles

Cursor Bite is designed around local-first processing, explicit user control, modular providers, and failure-safe behavior.

Before opening a pull request, please keep these principles in mind:

- Prefer local processing whenever a capability can work locally.
- Never send user content to an external service without an explicit product-level reason and clear disclosure.
- Keep provider-specific code behind domain-facing interfaces.
- Preserve clipboard safety and graceful degradation guarantees.
- Add or update tests for behavioral changes.
- Avoid logging user content, captured text, screenshots, credentials, or secrets.

## Development setup

1. Create and activate a Python virtual environment.
2. Install the core dependencies from `requirements-core.txt`.
3. Install optional dependencies from `requirements.txt` when working on those integrations.
4. Follow `SETUP_GUIDE.md` for Windows-specific components such as Tesseract, Ollama, and Argos Translate.

## Tests

Run the test suite before opening a pull request:

```bash
python -m pytest tests/ -q
```

Tests should remain runnable without network access, Ollama, Tesseract, Argos language packs, or a display whenever practical.

## Pull requests

Please keep pull requests focused and explain:

- what changed
- why it changed
- how it was tested
- any user-facing behavior changes
- any privacy or security implications

For larger changes, open an issue first so the architecture can be discussed before implementation.
