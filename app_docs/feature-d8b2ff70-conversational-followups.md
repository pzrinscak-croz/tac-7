# Conversational Follow-ups

**ADW ID:** d8b2ff70
**Date:** 2026-07-03
**Specification:** specs/issue-49-adw-d8b2ff70-sdlc_planner-conversational-follow-ups.md

## Overview

Adds conversational context to the natural-language-to-SQL workflow. After a query runs successfully, the app remembers the previous question and its generated SQL and automatically sends them with the next query. This lets the LLM interpret follow-ups like "now filter that by city" or "show that as percentages instead" without the user re-specifying tables and columns. A "Clear context" button and automatic reset on file upload return the app to standalone mode.

## What Was Built

- Optional `previous_query` / `previous_sql` fields on the server `QueryRequest` model (fully backward compatible, default `None`).
- A `format_previous_context` helper in the LLM processor that builds a labeled "Previous conversation context" block and injects it into both the OpenAI and Anthropic prompts.
- Client-side module state tracking the last *successful* `{ query, sql }` pair, sent with the next request.
- A "Continuing from: '{query}'" indicator label with a "Clear context" button in the query UI.
- Automatic context clearing on new file upload; failed queries never become context.
- Server unit tests and an E2E test (`test_conversational_followups`) covering the full loop.

## Technical Implementation

### Files Modified

- `app/server/core/data_models.py`: Added optional `previous_query` and `previous_sql` fields to `QueryRequest`.
- `app/server/core/llm_processor.py`: Added `format_previous_context()`; extended `generate_sql_with_openai` / `generate_sql_with_anthropic` to accept the optional context params and inject the block after the schema, before the "Convert this natural language query to SQL" line; `generate_sql` now forwards `request.previous_query`/`request.previous_sql` to every provider call site.
- `app/client/src/types.d.ts`: Mirrored the two optional fields on the `QueryRequest` interface.
- `app/client/src/main.ts`: Added `conversationContext` state, `updateContextIndicator()`, `clearConversationContext()`, `initializeClearContextButton()`; sends context with each request; only stores context when `!response.error`; clears context on successful upload.
- `app/client/index.html`: Added the hidden-by-default `#context-indicator` element with `#context-label` and `#clear-context-button`.
- `app/client/src/style.css`: Added styling for `.context-indicator`, `.context-label`, and `.clear-context-button`.
- `app/server/tests/core/test_llm_processor.py`: Added tests for the helper, prompt injection in both providers, `generate_sql` forwarding, and backward compatibility.
- `.claude/commands/e2e/test_conversational_followups.md`: New E2E test file.

### Key Changes

- Context is purely additive and optional — when the fields are absent, prompts and behavior are identical to the previous single-turn path (zero regressions).
- `format_previous_context` returns `""` unless **both** `previous_query` and `previous_sql` are present, so partial context is never injected.
- Only successful responses (`!response.error`) update the client context; thrown errors and server errors preserve any existing context.
- Both providers receive the identical context block, keeping behavior provider-independent.
- Long previous-query text is truncated to ~80 chars for the label display, but the full text is still sent to the server.

## How to Use

1. Upload a dataset (or load sample data) and run an initial query, e.g. "show all users".
2. A "Continuing from: 'show all users'" label appears below the query controls.
3. Ask a follow-up such as "filter that by city = 'New York'" — the generated SQL references the existing table without re-specifying it.
4. Click "Clear context" to return to standalone mode (the label disappears), or upload a new file to clear context automatically.

## Configuration

No new configuration or environment variables. The feature uses existing dependencies (FastAPI/Pydantic on the server, vanilla TypeScript on the client). SQL generation still requires `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` as before.

## Testing

- Server: `cd app/server && uv run pytest tests/core/test_llm_processor.py -v`
- Frontend type-check: `cd app/client && bun tsc --noEmit`
- Frontend build: `cd app/client && bun run build`
- E2E: start the app (`./scripts/start.sh`), then run `.claude/commands/e2e/test_conversational_followups.md` via the E2E test runner.

## Notes

- Context is single-turn (only the immediately previous query + SQL). Multi-turn history is out of scope.
- Context is only ever populated from a successful query, so broken SQL cannot poison the next follow-up.
- The two new request fields are optional on both server and client, so existing clients that don't send them behave exactly as before.
