# Security Policy

## Reporting a vulnerability

Please report security issues privately rather than opening a public issue.
Use GitHub's **Security Advisories** ("Report a vulnerability" under the
Security tab of this repository) so the report isn't visible until a fix is
ready. If that isn't available, open an issue asking a maintainer to contact
you privately rather than describing the vulnerability in public.

Please include:
- What you found and why it's a security concern.
- Steps to reproduce, or a proof of concept.
- The impact you believe it has (data exposure, code execution, privacy
  bypass, etc.).

We aim to acknowledge reports within a few days. This is a volunteer-run
open-source project without a formal SLA, but security reports are treated
as a priority over other issues.

## Threat model

Cursor Bite runs with the privileges of the logged-in user, reads clipboard
and selected-text content on demand, captures screen regions on demand, and
optionally sends text to a local (Ollama) or external (DuckDuckGo) service.
It is **not** a sandboxed process and does not attempt to defend against a
user who can already run arbitrary code as themselves — the threat model is
about what Cursor Bite itself does with the access it has, not about
defending the host from a malicious actor with local code execution.

In scope:
- Sensitive content (credentials, tokens, personal data) leaving the device
  without the user's knowledge or consent.
- The clipboard being corrupted or leaked (history retained, wrong content
  restored, restore failing silently).
- Logs containing user content (selected text, prompts, translations,
  search queries, screenshots).
- Command/shell injection via subprocess calls (Tesseract invocation, any
  future external-process integration).
- Path traversal or unsafe file handling.
- A dependency (Python package or the local design-prototype Node server)
  introducing a real vulnerability into a default install or workflow.

Out of scope:
- Attacks requiring the attacker to already have arbitrary code execution
  as the same Windows user Cursor Bite runs as.
- The local Ollama server's own security — Cursor Bite talks to
  `localhost:11434` and trusts responses from whatever is listening there,
  the same way any local Ollama client does.
- DuckDuckGo's own infrastructure or search result content.

## Known limitations (not vulnerabilities, but worth understanding)

- **The sensitive-data detector is regex-based**, documented in
  `infrastructure/privacy/detector.py`. It catches common patterns (emails,
  phone numbers, well-known credential/token shapes, Luhn-valid card
  numbers, private IP ranges) but is not a guarantee — a secret with an
  unusual shape, split across lines, or lacking a recognizable keyword can
  pass through undetected. Treat it as a safety net that reduces accidental
  leaks, not as a content-security boundary you can rely on absolutely.
- **Local processing is never blocked on sensitive-data grounds by design**
  (see the Privacy Model in README.md) — the detector only gates content
  that would leave the device. This is intentional, not an oversight: local
  tools that refuse to touch sensitive text stop being useful for exactly
  the documents you most want help with.
- **The `design/web-prototype/` folder is a developer-only mockup**, not
  part of the shipped application. Its local Node server proxies to Ollama
  with no authentication and should never be exposed beyond `localhost`.

## Supported versions

This project does not yet have tagged releases with independent security
support windows. Security fixes land on the `main` branch; please run the
latest commit.
