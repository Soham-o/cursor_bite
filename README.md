# Cursor Bite

> **Intelligence at your cursor.**
>
> A local-first, context-aware AI assistant for Windows that turns the information already on your screen into actions — without forcing you to leave your workflow.

<p align="center">
  <strong>AI Assistant · Desktop Overlay · Privacy First · Local AI · Automation</strong>
</p>

<p align="center">
  <a href="https://github.com/Soham-o/cursor_bite/stargazers"><img src="https://img.shields.io/github/stars/Soham-o/cursor_bite?style=flat-square" alt="GitHub stars"></a>
  <a href="https://github.com/Soham-o/cursor_bite/issues"><img src="https://img.shields.io/github/issues/Soham-o/cursor_bite?style=flat-square" alt="GitHub issues"></a>
  <a href="https://github.com/Soham-o/cursor_bite/blob/main/LICENSE"><img src="https://img.shields.io/github/license/Soham-o/cursor_bite?style=flat-square" alt="MIT License"></a>
  <img src="https://img.shields.io/badge/Python-3.11%2B-blue?style=flat-square" alt="Python 3.11+"><br>
  <img src="https://img.shields.io/badge/Platform-Windows-lightgrey?style=flat-square" alt="Windows">
  <img src="https://img.shields.io/badge/AI-Local--First-success?style=flat-square" alt="Local first AI">
</p>

---

## Why Cursor Bite?

Modern AI assistants usually make you **leave the context you are working in**: open a chat, copy text, paste it, ask a question, then return to the original application.

Cursor Bite takes the opposite approach.

**The interface comes to you.**

Select text in a browser, PDF, IDE, document, or chat. Press `Ctrl+Alt+B`. A radial HUD appears around your cursor and lets you translate, summarize, explain, rewrite, search, capture screen text, or ask AI — right where you are working.

The project is built around a simple engineering principle:

> **Context should be an input to intelligence, not something the user has to manually transport between applications.**

---

## What it can do

| Capability | What happens | Processing |
|---|---|---|
| **Translate** | Translate selected text into your configured language | Local / Argos Translate |
| **Summarize** | Turn selected content into a concise summary | Local / Ollama |
| **Explain** | Explain difficult text in context | Local / Ollama |
| **Rewrite** | Improve or transform selected text | Local / Ollama |
| **Ask AI** | Ask a free-form contextual question | Local / Ollama |
| **OCR** | Select any screen region and extract text | Local / Tesseract |
| **Web Search** | Search the web without opening a new workflow | External / DuckDuckGo |
| **Privacy Gateway** | Detect sensitive content before external actions | Local |

### Designed for the real desktop

- Global Windows hotkey
- Cursor-positioned radial interface
- Multi-monitor and DPI-aware positioning
- Clipboard snapshot + restoration
- System tray operation
- Lazy initialization of optional providers
- Graceful degradation when optional components are unavailable
- No telemetry
- No keylogging
- No persistent clipboard history
- No background screen recording

---

## Privacy architecture

Privacy is not a settings-page feature in Cursor Bite. It is part of the execution pipeline.

```text
                     USER CONTEXT
                          │
             selected text / screen region
                          │
                          ▼
                ┌──────────────────┐
                │ Context Provider │
                └────────┬─────────┘
                         │
                         ▼
                ┌──────────────────┐
                │ Privacy Gateway  │
                │                  │
                │ detect sensitive │
                │ data + policy    │
                └────────┬─────────┘
                         │
              ┌──────────┴──────────┐
              │                     │
          LOCAL PATH            EXTERNAL PATH
              │                     │
       ┌──────┼──────┐              │
       ▼      ▼      ▼              ▼
     OCR   AI/LLM  Translate      Search
  Tesseract Ollama  Argos       DuckDuckGo
              │                     │
              └──────────┬──────────┘
                         ▼
                  Result near cursor
```

Sensitive-data detection covers patterns such as emails, phone numbers, API keys, credit-card numbers, tokens, and private IP addresses. External actions can be blocked or require explicit consent according to the privacy policy.

The application also preserves the user's clipboard across context capture paths and avoids putting user content into logs.

---

## Architecture

Cursor Bite uses a **ports-and-adapters / hexagonal architecture** so the core application does not depend directly on a particular AI model, OCR engine, translation engine, or search provider.

```text
cursor_bite/
│
├── app/                  # Application orchestration and use cases
├── domain/               # Core interfaces and domain contracts
├── infrastructure/       # Provider implementations and OS integrations
├── ui/                   # PyQt6 overlays, HUD, result and settings views
├── config/               # Application configuration
├── tests/                # Automated behavioral tests
├── main.py               # Application entry point
├── SETUP_GUIDE.md        # Component-by-component setup
└── HOW_TO_USE.md         # User guide and keyboard reference
```

### Dependency direction

```text
        UI / Application
               │
               ▼
            Domain
               ▲
               │
       Infrastructure
```

The domain layer defines what the application needs. Infrastructure implements those capabilities. Providers are resolved lazily so an unavailable optional dependency does not prevent the application from starting.

### Two-phase execution

Actions use a `prepare()` → `execute()` model:

1. **Prepare** — capture context and determine the required policy.
2. **Consent boundary** — if an external action needs permission, the user is asked before transmission.
3. **Execute** — perform the selected operation.
4. **Present** — display the result beside the cursor.

This separation makes privacy decisions explicit and testable.

---

## Technology stack

**Core**

- Python 3.11+
- PyQt6
- pywin32

**Local intelligence**

- Ollama
- Argos Translate
- Tesseract OCR
- mss
- Pillow

**External integration**

- DuckDuckGo HTML search

**Engineering**

- pytest
- Ports-and-adapters architecture
- Lazy provider initialization
- Failure-safe optional integrations

---

## Quick start

### 1. Clone

```bash
git clone https://github.com/Soham-o/cursor_bite.git
cd cursor_bite
```

### 2. Create a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install the core dependencies

```powershell
pip install -r requirements-core.txt
```

### 4. Run

```powershell
python main.py
```

The application can start without optional AI/OCR/translation components. Install only the integrations you want to use.

For the complete Windows setup, see **[SETUP_GUIDE.md](SETUP_GUIDE.md)**.

---

## Keyboard controls

| Key | Action |
|---|---|
| `Ctrl+Alt+B` | Open Cursor Bite |
| `1` | Translate |
| `2` | Summarize |
| `3` | Explain |
| `4` | Web Search |
| `5` | Settings |
| `6` | OCR / Screen Capture |
| `7` | Rewrite |
| `8` | Ask AI |
| `Esc` | Close / cancel |

See **[HOW_TO_USE.md](HOW_TO_USE.md)** for the full interaction guide.

---

## Testing

The project includes a broad automated test suite covering core behavior such as:

- Privacy detection and policy decisions
- Pipeline actions
- Clipboard save/restore behavior
- Search rate limiting
- Optional-component degradation
- Two-phase consent behavior
- Radial HUD keyboard and mouse navigation

Run:

```bash
python -m pytest tests/ -q
```

The test suite is designed to avoid requiring a display, network access, Ollama, Tesseract, or Argos language packs for core behavioral coverage.

---

## Design decisions

### Local-first instead of cloud-first

AI, OCR, and translation can operate locally. This reduces latency, improves privacy, and makes the core workflow usable without a cloud account.

### Providers behind interfaces

The application is not tightly coupled to one AI runtime or one provider. Provider implementations can be replaced without rewriting the domain layer.

### Graceful degradation

Optional dependencies should remove only the capability they provide — not break the application.

### Explicit network boundary

Web search is intentionally different from local actions. External transmission is treated as a visible policy boundary rather than an invisible implementation detail.

### Clipboard safety as an invariant

Cursor Bite temporarily uses the clipboard for universal text capture but restores the previous clipboard state after the operation, including failure paths.

---

## Roadmap

- [ ] First-class downloadable Windows release
- [ ] Signed installer
- [ ] More local model/provider adapters
- [ ] Additional OCR improvements
- [ ] Richer contextual actions
- [ ] Configurable action plugins
- [ ] Performance profiling and startup optimization
- [ ] Expanded accessibility support
- [ ] More comprehensive integration tests

The roadmap is intentionally focused on turning Cursor Bite from a strong prototype into a polished desktop product.

---

## Project status

**Active development.**

Cursor Bite is a serious engineering project and an evolving exploration of **context-aware desktop AI, local-first intelligence, privacy-aware automation, and human-computer interaction**.

---

## Contributing

Contributions, bug reports, architecture discussions, and feature ideas are welcome.

Please read **[CONTRIBUTING.md](CONTRIBUTING.md)** before opening a pull request.

Security-related reports should follow **[SECURITY.md](SECURITY.md)**.

---

## License

MIT — see **[LICENSE](LICENSE)**.

---

<p align="center">
  <strong>Built by Soham Panda</strong><br>
  <sub>AI engineering • intelligent software • privacy-first systems</sub>
</p>
