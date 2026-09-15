# Web UI/UX Design Prototype

This folder is **not part of the Cursor Bite Windows application**. It is a
browser-based mockup used to explore the radial menu / result panel / privacy
indicator interaction design before those were built as the real product —
the PyQt6 Windows app in the repository root (`main.py` and everything under
`app/`, `ui/`, `domain/`, `infrastructure/`).

It renders a fake YouTube desktop page and overlays a JavaScript clone of the
radial menu on top of it, so the interaction design could be iterated on
quickly in a browser. `server.js` also proxies to a locally-running Ollama
instance and scrapes DuckDuckGo, so the mockup can show live AI/search output
rather than static fixtures.

## Why it's kept

As a reference for the interaction design decisions (hover states, result
panel layout, activation toast timing) that carried over into the real
PyQt6 UI. It is not maintained in lockstep with the shipped app and may
drift from it over time.

## Running it (optional, developer-only)

```bash
cd design/web-prototype
npm install   # none currently declared — the server uses only Node builtins
node server.js
```

Then open `http://localhost:3000`. Requires Node.js and, for the AI/search
panels to show real output, a running local Ollama instance — neither is a
dependency of the actual Cursor Bite application.

**Do not expose this server beyond localhost.** It proxies to local Ollama
with no authentication and is meant for a developer's own machine only.

## Relationship to the shipped app

None at runtime. No file under `app/`, `ui/`, `domain/`, or `infrastructure/`
imports or depends on anything here, and nothing here is invoked by
`main.py`. Treat this as a design artifact, not a second UI for the product.
