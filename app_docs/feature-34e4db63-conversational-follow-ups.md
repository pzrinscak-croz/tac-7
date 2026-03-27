# Conversational Follow-ups

**ADW ID:** 18
**Date:** 2026-03-27
**Specification:** specs/issue-34e4db63-adw-18-sdlc_planner-conversational-follow-ups.md

## Overview

Adds conversational follow-up support to the natural language SQL interface. After running a query, the next query automatically includes the previous question and generated SQL as context, enabling follow-ups like "now filter that by city" without re-specifying tables or conditions. A "Clear context" button resets to standalone mode.

## What Was Built

- Server-side conversation context injection into LLM prompts (OpenAI and Anthropic)
- Client-side state tracking of the last successful query/SQL pair
- "Continuing from: '{query}'" indicator shown when context is active
- "Clear context" button to reset conversation state
- Automatic context clearing on new CSV uploads and failed queries

## Technical Implementation

### Files Modified

- `app/server/core/data_models.py`: Added optional `previous_query` and `previous_sql` fields to `QueryRequest`
- `app/server/core/llm_processor.py`: Added `build_conversation_context()` helper and wired context into both OpenAI and Anthropic prompt construction paths
- `app/server/tests/core/test_llm_processor.py`: Added tests for prompt construction with/without conversation context
- `app/client/src/types.d.ts`: Extended `QueryRequest` interface with optional `previous_query` and `previous_sql` fields
- `app/client/src/main.ts`: Added context tracking state, context indicator UI logic, clear button handler, and context clearing on upload
- `app/client/src/style.css`: Added styles for the context indicator bar and clear button
- `app/client/index.html`: Added `#context-indicator` container element between query input and results

### Key Changes

- A shared `build_conversation_context()` function generates the context prompt section when both `previous_query` and `previous_sql` are present; returns empty string if either is missing (partial context is treated as no context)
- Context is injected into the LLM prompt just before the current query, instructing the model to interpret references like "that", "those results", and "filter it" using the previous query
- Client tracks `lastQuery` and `lastSql` as module-level state, only updating on successful (non-error) responses
- The context indicator truncates displayed queries to 50 characters with ellipsis

## How to Use

1. Upload a CSV file or load sample data
2. Enter a natural language query (e.g., "show all users") and submit
3. After results appear, a "Continuing from: 'show all users'" label appears below the query input
4. Enter a follow-up query referencing the previous results (e.g., "filter that by city = 'New York'") — the LLM uses the previous context to generate correct SQL
5. Click "Clear context" to return to standalone query mode
6. Uploading a new CSV automatically clears any active context

## Configuration

No additional configuration is required. The feature uses existing LLM provider settings and API keys.

## Testing

- **Unit tests:** `cd app/server && uv run pytest` — validates prompt construction with and without conversation context for both providers, including partial context handling
- **TypeScript check:** `cd app/client && bun tsc --noEmit`
- **Client build:** `cd app/client && bun run build`
- **E2E test:** Run the conversational follow-ups E2E test via `.claude/commands/e2e/test_conversational_follow_ups.md`

## Notes

- Conversation context is limited to a single previous query/SQL pair (not full chat history), keeping the implementation simple while covering common follow-up patterns
- No new dependencies were added — the feature uses existing Pydantic models, fetch API, and DOM manipulation
- Future enhancement: could extend to multi-turn context (array of previous queries) if deeper conversation flows are needed
