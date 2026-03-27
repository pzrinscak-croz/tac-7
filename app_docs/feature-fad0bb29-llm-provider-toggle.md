# LLM Provider Toggle

**ADW ID:** 29
**Date:** 2026-03-27
**Specification:** specs/issue-29-adw-fad0bb29-sdlc_planner-llm-provider-toggle.md

## Overview

Adds a dropdown to the UI that lets users switch between OpenAI and Anthropic as the LLM provider for natural language query processing. The selected provider persists across page reloads via localStorage. This is a client-only change — the server already supports both providers.

## What Was Built

- Provider `<select>` dropdown in the query controls area (next to Query and Upload buttons)
- localStorage persistence of the selected provider
- Dynamic `llm_provider` value in query request payloads (replacing the hardcoded `'openai'`)
- Styled dropdown matching existing UI controls

## Technical Implementation

### Files Modified

- `app/client/index.html`: Added `<select id="llm-provider-select">` with OpenAI and Anthropic options inside `.query-controls-left`
- `app/client/src/main.ts`: Added localStorage read/write for provider selection, replaced hardcoded `llm_provider: 'openai'` with dropdown value
- `app/client/src/style.css`: Added styles for `#llm-provider-select` using existing CSS variables (`--primary-color`, `--surface`, `--border-color`, `--text-primary`) with hover and focus states

### Key Changes

- The dropdown initializes from `localStorage.getItem('llm_provider')`, defaulting to `'openai'` if unset or invalid
- A `change` event listener on the dropdown saves the selection to localStorage immediately
- The `processQuery` call reads the dropdown's current value at query time, cast to the `'openai' | 'anthropic'` union type
- The dropdown styling matches existing button padding, border-radius, and color scheme with smooth hover/focus transitions
- `align-items: center` was added to `.query-controls-left` for proper vertical alignment

## How to Use

1. Open the application in your browser
2. Locate the provider dropdown next to the Query and Upload buttons
3. Select either "OpenAI" or "Anthropic" from the dropdown
4. Enter a natural language query and click Query
5. The query will be processed using the selected provider
6. Your selection persists across page reloads

## Configuration

No additional configuration is required. The server must have the relevant API key configured for the selected provider:
- OpenAI: `OPENAI_API_KEY` environment variable
- Anthropic: `ANTHROPIC_API_KEY` environment variable

If only one API key is configured, the server's `generate_sql` function will use that provider regardless of the client selection.

## Testing

- TypeScript type checking: `cd app/client && bun tsc --noEmit`
- Frontend build: `cd app/client && bun run build`
- Server tests: `cd app/server && uv run pytest`
- E2E test: `.claude/commands/e2e/test_llm_provider_toggle.md`

## Notes

- The `generate_random_query` endpoint does not respect the provider toggle — it uses its own key-availability-based routing
- The server prioritizes API key availability over the `llm_provider` request field; if only one key is configured, that provider is used regardless of the dropdown selection
