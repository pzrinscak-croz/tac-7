# Feature: Conversational Follow-ups

## Metadata
issue_number: `49`
adw_id: `d8b2ff70`
issue_json: `{"number":49,"title":"Conversational Follow-ups","body":"/feature\n\nadw_sdlc_iso\n\nmodel_set heavy\n\nAfter running a query, the next query automatically includes the previous question + generated SQL as context. The LLM can reference prior results to handle follow-ups like \"now filter that by city\" or \"show that as percentages instead.\" A \"Clear context\" button resets to standalone mode.\n\n**Scope:**\n- Server: Add optional previous_query and previous_sql fields to QueryRequest, include them in the LLM prompt\n- Client: Track last query/SQL pair, send with next request, show a small \"continuing from...\" label\n\n**Acceptance criteria:**\n1. Run \"show all users\", then \"filter that by city = 'New York'\" -- the second query produces correct SQL without re-specifying the table\n2. A \"Continuing from: '{query}'\" label is visible when context is active\n3. Clicking \"Clear context\" removes the label; the next query is standalone\n4. Failed queries do not carry forward as context\n5. Uploading a new CSV clears existing context"}`

## Feature Description
This feature adds conversational context to the natural-language-to-SQL workflow. After a user successfully runs a query, the application remembers the previous natural language question and the SQL that was generated for it. When the user submits their next query, that prior question + SQL pair is automatically sent to the server and injected into the LLM prompt as context.

This lets the LLM correctly interpret follow-up questions that reference the previous result implicitly, such as:
- "now filter that by city" (after "show all users")
- "show that as percentages instead"
- "only the top 5"

A small "Continuing from: '{previous query}'" label is displayed in the UI whenever context is active, so the user always knows whether their next query will be interpreted as a follow-up or as a standalone query. A "Clear context" button lets the user reset back to standalone mode at any time. Context is also automatically cleared whenever a new CSV/JSON file is uploaded (since the schema may have changed) and is never populated by failed queries.

## User Story
As a user querying my data with natural language
I want the app to remember my previous question and its SQL so I can ask follow-up questions like "now filter that by city"
So that I can iteratively refine results conversationally without re-specifying tables and columns every time

## Problem Statement
Today every query is fully independent. The `/api/query` endpoint receives only the current natural language `query` and the database schema, with no memory of what the user asked before. This means a follow-up like "now filter that by city = 'New York'" fails or produces incorrect SQL because the LLM has no idea what "that" refers to — there is no table, columns, or prior SQL in scope. Users are forced to re-state the full query every time they want to refine a result, which is tedious and breaks the conversational experience users expect from a natural-language interface.

## Solution Statement
Add an optional conversational context channel end-to-end:

1. **Server**: Extend `QueryRequest` with optional `previous_query` and `previous_sql` fields. When present, inject a clearly-labeled "Previous conversation context" block into the LLM prompt (for both OpenAI and Anthropic providers) instructing the model to treat the new query as a potential follow-up that may reference the prior question/SQL. When absent, behavior is unchanged (fully backward compatible / standalone mode).

2. **Client**: Track the last *successful* `{query, sql}` pair in module-level state. Send it with the next `processQuery` request. Render a small "Continuing from: '{query}'" label with a "Clear context" button whenever context is active. Clear the context (and hide the label) when the user clicks "Clear context" or uploads a new file. Never store context from a failed query.

The design keeps the existing single-turn code path intact — context is purely additive and optional — so there are zero regressions for standalone queries.

## Relevant Files
Use these files to implement the feature:

- `README.md` - Project overview, API endpoints, and start/stop commands. Read first to understand structure and how to run the app.
- `app/server/core/data_models.py` - Contains `QueryRequest`/`QueryResponse` Pydantic models. Add the two optional context fields to `QueryRequest` here.
- `app/server/core/llm_processor.py` - Contains `generate_sql`, `generate_sql_with_openai`, `generate_sql_with_anthropic`, and `format_schema_for_prompt`. This is where the previous-context block is built and injected into both provider prompts. `generate_sql` must forward the new fields from the request.
- `app/server/server.py` - Contains the `POST /api/query` endpoint (`process_natural_language_query`). No signature change needed (it already passes the full `request` to `generate_sql`), but verify the flow and that errors do not leak context.
- `app/server/tests/core/test_llm_processor.py` - Existing unit tests for the LLM processor. Add tests covering the new context behavior here, following the existing mock/patch patterns.
- `app/client/src/types.d.ts` - Frontend `QueryRequest` interface must be kept in exact sync with the Pydantic model; add the two optional fields.
- `app/client/src/api/client.ts` - `api.processQuery` serializes and sends the `QueryRequest`. No change needed unless the request object is reshaped, but review it.
- `app/client/src/main.ts` - Core client logic. Add conversational-context state, send context with the next query, only store context on success, render/update the "Continuing from" label + "Clear context" button, and clear context on upload.
- `app/client/index.html` - Add the DOM elements for the context indicator label and "Clear context" button inside the query section.
- `app/client/src/style.css` - Add styling for the context indicator label and clear-context button. Read this file before making style changes (per conditional docs).
- `app_docs/feature-4c768184-model-upgrades.md` - Conditional documentation relevant to the `llm_processor` module and SQL query generation. Read before modifying prompts/model behavior to stay consistent with existing conventions.
- `.claude/commands/test_e2e.md` - Read to understand how the E2E test runner executes `.md` test files (used for the validation step).
- `.claude/commands/e2e/test_basic_query.md` - Read as the reference/example format for authoring the new E2E test file.

### New Files
- `.claude/commands/e2e/test_conversational_followups.md` - New E2E test file (in the E2E test format) validating the conversational follow-up flow, the context label, the "Clear context" button, and that uploads clear context.

## Implementation Plan
### Phase 1: Foundation
Establish the data contract for conversational context across the server and client boundary:
- Add optional `previous_query` and `previous_sql` fields to the server-side `QueryRequest` Pydantic model (defaulting to `None`, fully backward compatible).
- Mirror those fields as optional properties on the client-side `QueryRequest` TypeScript interface so the two stay exactly in sync (the file comment mandates this).

### Phase 2: Core Implementation
Implement the actual context-aware behavior:
- **Server**: Add a small helper in `llm_processor.py` that formats a "Previous conversation context" block from `previous_query` + `previous_sql`. Extend `generate_sql_with_openai` and `generate_sql_with_anthropic` to accept optional previous context and inject the block into their prompts (with instructions to treat the new query as a possible follow-up). Update `generate_sql` to forward `request.previous_query` and `request.previous_sql` to whichever provider function it routes to.
- **Client**: Add module-level `conversationContext` state (`{ query, sql } | null`). In `executeQuery`, include the context on the outgoing request, and after a *successful* response (no `response.error`), set the context to the current `{ query, sql }`. Add UI rendering to show/hide the "Continuing from: '{query}'" label and its "Clear context" button.

### Phase 3: Integration
Wire the context lifecycle into existing flows:
- Add the DOM elements (label + clear button) to `index.html` and style them in `style.css`.
- Hook the "Clear context" button to reset state and hide the label.
- Clear context inside `handleFileUpload` (successful upload path) so a new dataset starts fresh.
- Ensure failed queries (thrown errors or `response.error`) never update the context.
- Author and run the E2E test to validate the full loop.

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

### 1. Read reference documentation
- Read `README.md`, `app_docs/feature-4c768184-model-upgrades.md`, `.claude/commands/test_e2e.md`, and `.claude/commands/e2e/test_basic_query.md` to confirm conventions before making changes.

### 2. Extend the server `QueryRequest` model
- In `app/server/core/data_models.py`, add two optional fields to `QueryRequest`:
  - `previous_query: Optional[str] = Field(None, description="Previous natural language query for conversational context")`
  - `previous_sql: Optional[str] = Field(None, description="SQL generated for the previous query")`
- Keep them optional with `None` defaults so existing standalone requests remain valid.

### 3. Add previous-context formatting + prompt injection in the LLM processor
- In `app/server/core/llm_processor.py`, add a helper function `format_previous_context(previous_query: Optional[str], previous_sql: Optional[str]) -> str` that returns an empty string when either value is missing, otherwise returns a labeled block such as:
  ```
  Previous conversation context (the user may be asking a follow-up that references this):
  - Previous question: "{previous_query}"
  - Previous SQL: {previous_sql}

  If the new query is a follow-up (e.g. "filter that by city", "show as percentages", "only the top 5"),
  build upon the previous SQL and its tables/columns. If it is unrelated, ignore this context.
  ```
- Update `generate_sql_with_openai(query_text, schema_info, previous_query=None, previous_sql=None)` and `generate_sql_with_anthropic(query_text, schema_info, previous_query=None, previous_sql=None)` to accept the optional params (backward compatible defaults) and insert the formatted context block into the prompt (place it after the schema, before "Convert this natural language query to SQL").
- Update `generate_sql(request, schema_info)` so every call site passes `request.previous_query` and `request.previous_sql` through to the chosen provider function.
- Do NOT use decorators; keep the change minimal and consistent with the existing prompt style.

### 4. Verify the server query endpoint
- In `app/server/server.py`, confirm `process_natural_language_query` still passes the full `request` object to `generate_sql` (no change needed). Confirm that on error the endpoint returns `QueryResponse` with `error` set and does not require the new fields.

### 5. Add server unit tests
- In `app/server/tests/core/test_llm_processor.py`, add tests following existing mock/patch conventions:
  - `format_previous_context` returns `""` when `previous_query`/`previous_sql` are `None`.
  - `format_previous_context` includes both the previous question and previous SQL when provided.
  - `generate_sql_with_openai` includes the previous context block in the prompt when context is provided (assert on the captured prompt via the mock call args).
  - `generate_sql_with_anthropic` includes the previous context block in the prompt when context is provided.
  - `generate_sql` forwards `previous_query`/`previous_sql` from a `QueryRequest` to the provider function (assert call args include the context values).
  - Standalone request (no context) still works and produces no context block (backward compatibility).

### 6. Sync the client `QueryRequest` type
- In `app/client/src/types.d.ts`, add optional fields to the `QueryRequest` interface:
  - `previous_query?: string;`
  - `previous_sql?: string;`

### 7. Add conversational-context state and logic in the client
- In `app/client/src/main.ts`, add module-level state: `let conversationContext: { query: string; sql: string } | null = null;`
- In `executeQuery`:
  - Build the request including `previous_query`/`previous_sql` from `conversationContext` when it is set.
  - After the `await api.processQuery(...)` call, only update context on success: if `!response.error`, set `conversationContext = { query, sql: response.sql }` and call the label-update function. (Errors thrown by the request must NOT touch context.)
- Add a helper `updateContextIndicator()` that shows the "Continuing from: '{conversationContext.query}'" label + "Clear context" button when context is set, and hides them when it is `null`. Truncate long queries for display if needed.
- Add a helper `clearConversationContext()` that sets `conversationContext = null` and calls `updateContextIndicator()`.
- Wire the "Clear context" button's click handler to `clearConversationContext()`.
- In `handleFileUpload`, on successful upload call `clearConversationContext()` so a new dataset starts standalone.

### 8. Add the context indicator DOM elements
- In `app/client/index.html`, add a hidden-by-default context indicator inside the `query-section` (e.g. below the textarea, near `query-controls`):
  ```html
  <div id="context-indicator" class="context-indicator" style="display: none;">
    <span id="context-label" class="context-label"></span>
    <button id="clear-context-button" class="clear-context-button">Clear context</button>
  </div>
  ```

### 9. Style the context indicator
- Read `app/client/src/style.css` first, then add styles for `.context-indicator`, `.context-label`, and `.clear-context-button` consistent with existing button/label styling (small, subtle, secondary appearance).

### 10. Create the E2E test file
- Create `.claude/commands/e2e/test_conversational_followups.md` modeled on `.claude/commands/e2e/test_basic_query.md`. It must:
  - Navigate to the `Application URL` and load the Users sample data (via the Upload modal → "Users Data" sample button) so a known `users` table exists.
  - Run "show all users", verify results + SQL appear.
  - **Verify** the "Continuing from: 'show all users'" label is now visible (screenshot).
  - Run a follow-up "filter that by city = 'New York'" and **verify** the generated SQL references the `users` table without the user re-specifying it (e.g. contains `FROM users` and a `city` filter). Screenshot the SQL.
  - Click "Clear context" and **verify** the label disappears (screenshot).
  - Keep it to the minimal set of steps with screenshots proving the behavior.

### 11. Run all validation commands
- Execute every command in the `Validation Commands` section and ensure they all pass with zero regressions, including the new E2E test.

## Testing Strategy
### Unit Tests
- **`format_previous_context`**: returns `""` for missing/`None` inputs; returns a block containing both the previous question and previous SQL when both provided.
- **`generate_sql_with_openai` / `generate_sql_with_anthropic`**: when context is provided, the prompt passed to the mocked client contains the previous question and previous SQL; when no context, the prompt contains no context block. Existing success/markdown-cleanup/no-key/error tests must continue to pass unchanged.
- **`generate_sql` routing**: forwards `previous_query`/`previous_sql` from the `QueryRequest` to the selected provider function; existing priority/fallback routing tests still pass.
- **Backward compatibility**: a `QueryRequest` created without the new fields validates and behaves exactly as before.

### Edge Cases
- `previous_query` set but `previous_sql` missing (or vice versa) → no context block injected (helper returns `""`).
- First-ever query in a session → no context sent (standalone).
- Failed query (`response.error` present, or network/HTTP error thrown) → context is NOT updated; a previously valid context (if any) is preserved.
- Uploading a new file while context is active → context cleared and label hidden.
- Clicking "Clear context" when there is no active context → no error, label stays hidden.
- Very long previous query text → label is truncated for display but full text still sent to the server.
- Follow-up query that is actually unrelated → LLM prompt instructs it to ignore stale context (best-effort; verified qualitatively).

## Acceptance Criteria
1. Running "show all users" then "filter that by city = 'New York'" produces correct SQL for the second query that references the `users` table without the user re-specifying it (context is sent and injected into the prompt).
2. A "Continuing from: '{query}'" label is visible whenever conversational context is active.
3. Clicking "Clear context" removes the label and the next query is sent standalone (no `previous_query`/`previous_sql`).
4. A failed query (server `error` or thrown request error) does not become context and does not overwrite existing context.
5. Uploading a new CSV/JSON file clears any existing context and hides the label.
6. Standalone queries continue to work exactly as before (zero regressions); the new request fields are optional on both server and client.
7. All server unit tests, frontend type-check, frontend build, and the new E2E test pass.

## Validation Commands
Execute every command to validate the feature works correctly with zero regressions.

- `cd app/server && uv run pytest` - Run server tests to validate the feature works with zero regressions.
- `cd app/server && uv run pytest tests/core/test_llm_processor.py -v` - Run the LLM processor tests specifically to confirm the new context tests pass.
- `cd app/client && bun tsc --noEmit` - Type-check the frontend (confirms `QueryRequest` types stay in sync and there are no type errors).
- `cd app/client && bun run build` - Build the frontend to validate the feature compiles for production with zero regressions.
- Read `.claude/commands/test_e2e.md`, then read and execute your new E2E `.claude/commands/e2e/test_conversational_followups.md` test file to validate this functionality works end-to-end (start the app first with `./scripts/start.sh`).

## Notes
- No new libraries are required; this feature is implemented entirely with existing dependencies (FastAPI/Pydantic on the server, vanilla TypeScript on the client).
- The two new `QueryRequest` fields are optional with `None`/`undefined` defaults, keeping the API fully backward compatible — any existing client that does not send them behaves exactly as before.
- The context is intentionally kept to just the *immediately* previous query + SQL (single-turn memory), matching the issue scope. A future enhancement could maintain a longer multi-turn history, but that is out of scope here.
- Context must only ever be populated from a **successful** query (`response.error` falsy and no thrown error) so that broken SQL never poisons the next follow-up.
- Keep prompt changes minimal and consistent with the existing prompt style in `llm_processor.py`; both the OpenAI and Anthropic prompts must receive the same context block so behavior is provider-independent.
- Per project conventions: no decorators, keep it simple, and follow existing mock/patch patterns in the test suite.
