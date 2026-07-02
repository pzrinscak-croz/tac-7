# Conversational Follow-ups

**ADW ID:** ed38128c
**Date:** 2026-07-03
**Specification:** specs/issue-47-adw-ed38128c-sdlc_planner-conversational-follow-ups.md

## Overview

Adds conversational memory to the Natural Language SQL Interface. After a successful query, the previous natural language question and its generated SQL are automatically carried forward as context into the next query, letting the LLM interpret follow-ups like "filter that by city = 'New York'" or "show that as percentages instead" without re-specifying the table. A "Continuing from: '{query}'" label plus a "Clear context" button let users see and reset the active context.

## What Was Built

- Two optional request fields — `previous_query` and `previous_sql` — shared across the server Pydantic model and the client TypeScript interface.
- A prompt helper (`format_previous_context`) that injects a delimited "follow-up" block into the LLM prompt when prior-turn context is present.
- Prompt threading through both provider paths (`generate_sql_with_openai`, `generate_sql_with_anthropic`) and the router (`generate_sql`).
- Client-side context state that tracks the last successful `(query, sql)` pair and sends it with the next request.
- A "Continuing from: '{query}'" indicator label with a "Clear context" button in the query section.
- Context reset on both "Clear context" clicks and successful CSV/JSON uploads.
- Unit tests for prompt inclusion/exclusion and routing pass-through, plus an E2E test file.

## Technical Implementation

### Files Modified

- `app/server/core/data_models.py`: Added `previous_query` and `previous_sql` optional fields to `QueryRequest` (after `table_name`).
- `app/server/core/llm_processor.py`: Added `format_previous_context()` helper; extended both provider functions with optional `previous_query`/`previous_sql` args that inject the context block between the schema and the conversion instruction; updated `generate_sql` to forward the fields on all routing paths.
- `app/server/tests/core/test_llm_processor.py`: Added tests asserting the prompt contains prior question/SQL when context is set, omits the follow-up marker when absent, and that `generate_sql` forwards the fields to the provider.
- `app/client/src/types.d.ts`: Mirrored the two optional fields on the `QueryRequest` interface.
- `app/client/src/main.ts`: Added module-level `previousQuery`/`previousSql` state, `updateContextIndicator()`, `clearConversationContext()`, and `initializeClearContextButton()`; sends context with each request and updates it only on success; clears context on upload success.
- `app/client/index.html`: Added the hidden `#context-indicator` container with the label span and clear-context button.
- `app/client/src/style.css`: Added `.context-indicator`, `.context-label` (italic, muted, ellipsis-truncated), and `.clear-context-button` styles.
- `.claude/commands/e2e/test_conversational_followups.md`: New E2E test validating the follow-up flow, label, clear button, and upload reset.

### Key Changes

- `format_previous_context()` returns an empty string unless BOTH `previous_query` and `previous_sql` are truthy, so partial or empty context is safely treated as no context.
- The context block is inserted between the schema description and the "Convert this natural language query to SQL" instruction; the existing rules list is untouched.
- All new arguments and fields are optional with `None`/`undefined` defaults, keeping the change fully backward compatible.
- The client updates stored context only when `!response.error`, so failed queries never poison subsequent turns.
- `previous_sql` is only inserted into the prompt — never executed as-is; the follow-up SQL is regenerated and still passes through the existing SQL injection protection layer.

## How to Use

1. Run a query, e.g. "show all users". Results and SQL appear as usual.
2. A "Continuing from: 'show all users'" label and a "Clear context" button appear below the query controls.
3. Enter a follow-up such as "filter that by city = 'New York'". The LLM reuses the prior table/columns and produces correct SQL without re-specifying the table.
4. Click "Clear context" to reset to standalone mode — the label disappears and the next query is sent with no prior context.
5. Uploading a new dataset automatically clears the context.

## Configuration

No new configuration or environment variables. Reuses the existing FastAPI/Pydantic and Vite/TypeScript stacks; no new libraries.

## Testing

- `cd app/server && uv run pytest tests/core/test_llm_processor.py -v` — verifies prompt inclusion/exclusion and routing pass-through.
- `cd app/server && uv run pytest` — full server suite, zero regressions.
- `cd app/client && bun tsc --noEmit && bun run build` — type-check and build the client.
- Execute `.claude/commands/e2e/test_conversational_followups.md` end-to-end (start the app first per README).

## Notes

- Context is intentionally limited to a single prior turn (last query + last SQL), not a full multi-turn history. A future enhancement could maintain a bounded conversation history.
- The context indicator label truncates long queries visually via CSS (`max-width: 60ch` with ellipsis) while still sending the full value to the server.
