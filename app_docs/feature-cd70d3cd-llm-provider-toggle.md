# LLM Provider Toggle

**ADW ID:** 15
**Date:** 2026-03-27
**Specification:** specs/issue-cd70d3cd-adw-15-sdlc_planner-llm-provider-toggle.md

## Overview

Adds a visible provider selector dropdown to the query controls area, allowing users to switch between OpenAI and Anthropic as their LLM provider at runtime. The selected provider is persisted in `localStorage` so the preference survives page reloads. No backend changes were required — the server already routes queries based on the `llm_provider` field.

## What Was Built

- `<select id="provider-select">` dropdown in the query controls bar with options for OpenAI and Anthropic
- `initializeProviderSelect()` function in `main.ts` that loads the saved provider from `localStorage` on startup and persists changes on selection
- Live read of the dropdown value at query-submit time, replacing the previously hardcoded `'openai'` string
- CSS styling for `.provider-select` that matches the existing secondary-button aesthetic (border, border-radius, font, hover/focus states)

## Technical Implementation

### Files Modified

- `app/client/index.html`: Added `<select id="provider-select" class="provider-select">` with `openai` and `anthropic` options inside `.query-controls-left`, between the Query and Upload buttons
- `app/client/src/main.ts`: Added `initializeProviderSelect()` function (localStorage init + change listener); replaced hardcoded `llm_provider: 'openai'` with live dropdown read; called the new function at app startup
- `app/client/src/style.css`: Added `.provider-select` styles (padding, font, border using `--primary-color`, border-radius, hover invert, focus ring); added `align-items: center` to `.query-controls-left`

### Key Changes

- The hardcoded `llm_provider: 'openai'` at `main.ts:57` is replaced with `(document.getElementById('provider-select') as HTMLSelectElement).value as 'openai' | 'anthropic'`, read at query-submit time — no race condition risk
- `localStorage` key `llm_provider` mirrors the API field name for naming consistency
- Default value falls back to `'openai'` when no `localStorage` entry exists (first visit)
- The dropdown uses `var(--primary-color)` for border and text, maintaining visual consistency with the existing design system

## How to Use

1. Open the application in a browser
2. Locate the provider dropdown in the query controls bar (between the Query and Upload buttons)
3. Select **OpenAI** or **Anthropic** from the dropdown
4. Enter a query and click **Query** — the chosen provider processes the request
5. The selection is automatically saved; reloading the page retains your chosen provider

## Configuration

- Both `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` must be set in the server environment for both options to return valid results
- If only one key is configured, selecting the unsupported provider will produce a server-side error
- The `localStorage` key used for persistence is `llm_provider`

## Testing

Run the E2E test to validate the full toggle flow:

```bash
# Read and run the provider toggle E2E test
# .claude/commands/e2e/test_llm_provider_toggle.md
```

The test verifies: dropdown visibility, default selection (OpenAI), provider persistence across page reload, and that a query succeeds when Anthropic is selected.

Run server tests and TypeScript checks for regression validation:

```bash
cd app/server && uv run pytest
cd app/client && bun tsc --noEmit
cd app/client && bun run build
```

## Notes

- No backend changes are needed; the server already accepts and routes `llm_provider: "openai" | "anthropic"`
- See `app_docs/feature-4c768184-model-upgrades.md` for the current model versions used by each provider (Claude Sonnet 4 for Anthropic, GPT-4.1 for OpenAI)
- Corrupt or unknown `localStorage` values fall back to the first dropdown option (`openai`) via native `<select>` behavior
