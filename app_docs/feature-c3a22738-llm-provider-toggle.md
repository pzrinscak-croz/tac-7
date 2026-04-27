# LLM Provider Toggle

**ADW ID:** c3a22738
**Date:** 2026-04-27
**Specification:** specs/issue-32-adw-c3a22738-sdlc_planner-add-llm-provider-toggle.md

## Overview

Adds a visible provider selector to the query controls so users can choose between OpenAI and Anthropic before running a natural-language query. The selection is sent in the existing `llm_provider` field on `POST /api/query` and is persisted in `localStorage` so it survives page reloads. No backend changes were required — the server already accepts both providers.

## What Was Built

- Provider `<select>` dropdown rendered inline with the Query and Upload buttons.
- `localStorage`-backed persistence under the key `llm_provider` (defaults to `"openai"`).
- Wiring of the dropdown's current value into the `executeQuery` request body in place of the previously hardcoded `'openai'`.
- CSS styling for `#llm-provider-select` matching the existing button surface tokens.
- New E2E test (`.claude/commands/e2e/test_llm_provider_toggle.md`) covering visibility, default, persistence across reload, and successful queries with each provider.

## Technical Implementation

### Files Modified

- `app/client/index.html`: Added `<select id="llm-provider-select">` with `OpenAI` and `Anthropic` options inside `.query-controls-left`, after the Upload button. Includes `aria-label="LLM Provider"` for accessibility.
- `app/client/src/main.ts`: Added `PROVIDER_STORAGE_KEY` constant, `getStoredProvider()` / `setStoredProvider()` helpers (typed against `QueryRequest["llm_provider"]`), and `initializeProviderSelector()` invoked from the existing `DOMContentLoaded` handler. Replaced the hardcoded `llm_provider: 'openai'` in `executeQuery` with a read of the dropdown's current value.
- `app/client/src/style.css`: Added `#llm-provider-select` and `:focus` rules using `--border-color`, `--surface`, `--text-primary`, and `--primary-color`. Added `align-items: center` to `.query-controls-left` so the select sits inline with the buttons.
- `.claude/commands/e2e/test_llm_provider_toggle.md`: New E2E test specification.

### Key Changes

- Provider state is stored client-side only; the server is unaware of the selection beyond the request body it receives.
- `getStoredProvider()` validates the stored value against the `"openai" | "anthropic"` union and falls back to `"openai"` when `localStorage` returns `null` or any other value, so a tampered key cannot crash the app.
- The dropdown is hydrated from storage *before* `initializeQueryInput`, so the very first query after page load already uses the persisted provider.
- All existing query, upload, random-query, export, and debounce flows are untouched — only the `llm_provider` field's source changed.

## How to Use

1. Open the application in a browser.
2. Locate the **Provider** dropdown next to the **Query** and **Upload** buttons.
3. Select **OpenAI** or **Anthropic**.
4. Enter a natural-language query and click **Query** — the request is routed using the selected provider (`llm_provider` in the request payload).
5. Reload the page; the dropdown remembers your last selection.

## Configuration

- **Storage key:** `localStorage["llm_provider"]` — values: `"openai"` or `"anthropic"`. Default: `"openai"`.
- **Server API keys:** `OPENAI_API_KEY` and/or `ANTHROPIC_API_KEY` must be configured in the server environment for the chosen provider to actually return results.
- **Backend routing nuance:** `generate_sql()` in `app/server/core/llm_processor.py` currently prioritizes API-key availability over `request.llm_provider`. When only one key is set, the server may route to that provider regardless of the dropdown's value. The dropdown's persistence and request payload still match the user's selection — this only affects which model the server actually invokes.

## Testing

- Type-check: `cd app/client && bun tsc --noEmit`
- Build: `cd app/client && bun run build`
- Server tests (regression safety): `cd app/server && uv run pytest`
- New E2E flow: read `.claude/commands/test_e2e.md`, then execute `.claude/commands/e2e/test_llm_provider_toggle.md` via the Playwright MCP. Validates dropdown visibility, default value, persistence across reload, and successful queries with both providers.
- Existing regression: `.claude/commands/e2e/test_basic_query.md` confirms the default-OpenAI path still works end-to-end.

## Notes

- No new dependencies — uses the browser `localStorage` API and existing types.
- Adding a third provider in the future requires: a new `<option>`, an extension to the `Literal["openai", "anthropic"]` union in both `app/client/src/types.d.ts` and `app/server/core/data_models.py`, and a new generator branch in `llm_processor.py`.
- A visible `<label>` was intentionally omitted in favor of `aria-label` to keep the controls compact; if a visible label is preferred later, a `<label for="llm-provider-select">Provider</label>` can be inserted before the select with no layout changes.
