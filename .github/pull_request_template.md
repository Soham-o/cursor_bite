## What this changes and why

## Testing

- [ ] `python -m pytest tests/ -q` passes locally
- [ ] `ruff check .` passes locally
- [ ] If this touches the clipboard, selection capture, the privacy
      gateway, or logging: I re-read the relevant invariant in README.md's
      Privacy Model and this change doesn't violate it (no user content in
      logs, no unnecessary retention, sensitive data still blocked/consent-gated
      for external processing only).
- [ ] If this adds a new dependency: it's free, doesn't require an API key
      or account, and the app still starts and runs with it absent.

## Screenshots / recording

(For any UI change — before/after if it's a visual tweak.)
