# Cursor Bite — Project Overview

## One-line pitch

Cursor Bite is a context-aware Windows AI assistant that brings useful AI actions directly to the user's cursor while keeping local processing local.

## The problem

Desktop users constantly move information between applications to use AI. That creates context switching, repeated copy/paste operations, and unnecessary exposure of sensitive content to external services.

## The product idea

Cursor Bite turns the cursor into an interaction point for contextual intelligence.

```text
See something → invoke Cursor Bite → choose an action → get the result beside it
```

## Engineering goals

1. Minimize context switching.
2. Prefer local processing.
3. Make external data transmission explicit.
4. Keep integrations replaceable.
5. Degrade gracefully when optional components are unavailable.
6. Keep user content out of persistent logs and telemetry.

## Core flow

```text
Global Hotkey
     ↓
Cursor-aware HUD
     ↓
Context acquisition
     ↓
Privacy policy evaluation
     ↓
Local or external provider
     ↓
Result presentation
```

## What makes it technically interesting

### Context acquisition

The system can work with selected text as well as screen regions that require OCR. This means the assistant is not limited to applications that expose copyable text.

### Provider abstraction

AI, OCR, translation, search, and text-to-speech capabilities are treated as replaceable providers rather than being embedded throughout the application.

### Privacy gateway

The privacy layer inspects content before an action crosses the external boundary. This makes privacy a property of the pipeline rather than a user preference hidden in configuration.

### Failure isolation

Optional integrations are initialized only when needed. A missing optional dependency should disable one capability instead of preventing the entire application from launching.

## Engineering principles

- Local-first
- Explicit consent
- Least data movement
- Modular architecture
- Testable boundaries
- User-controlled context
- No hidden telemetry

## Current direction

The next stage is productization: packaging, signed distribution, performance optimization, richer contextual actions, provider plugins, and stronger integration testing.
