# Feature: Conversational Follow-ups

## Metadata
issue_number: `47`
adw_id: `ed38128c`
issue_json: `{"number":47,"title":"Conversational Follow-ups","body":"/feature\n\nadw_sdlc_iso\n\nmodel_set heavy\n\nAfter running a query, the next query automatically includes the previous question + generated SQL as context. The LLM can reference prior results to handle follow-ups like \"now filter that by city\" or \"show that as percentages instead.\" A \"Clear context\" button resets to standalone mode.\n\n**Scope:**\n- Server: Add optional `previous_query` and `previous_sql` fields to `QueryRequest`, include them in the LLM prompt\n- Client: Track last query/SQL pair, send with next request, show a small \"continuing from...\" label\n\n**Acceptance criteria:**\n1. Run \"show all users\", then \"filter that by city = 'New York'\" -- the second query produces correct SQL without re-specifying the table\n2. A \"Continuing from: '{query}'\" label is visible when context is active\n3. Clicking \"Clear context\" removes the label; the next query is standalone\n4. Failed queries do not carry forward as context\n5. Uploading a new CSV clears existing context"}`

## Feature Description
This feature adds conversational memory to the Natural Language SQL Interface. After a user runs a successful query, the previous natural language question and its generated SQL are automatically carried forward as context into the next query. This lets the LLM interpret follow-up requests that reference prior results — for example, running "show all users" and then "filter that by city = 'New York'" produces correct SQL without the user re-specifying the table.

A small visual "Continuing from: '{previous query}'" label appears when conversational context is active. A "Clear context" button next to the label resets the interface to standalone (single-shot) mode, discarding the carried-forward context. Context is only ever carried forward from queries that succeeded, and any CSV/JSON upload clears the existing context since the underlying data may have changed.

This delivers value by making the interface feel conversational and iterative: users can refine and reshape queries in natural steps rather than composing a complete, self-contained query every time.

## User Story
As a data analyst using the Natural Language SQL Interface
I want each follow-up query to remember my previous question and its SQL
So that I can iteratively refine results ("now filter that by city", "show that as percentages instead") without repeating the full context each time

## Problem Statement
Currently every query is fully standalone. The `/api/query` endpoint receives only the current `query` string and generates SQL against the schema with no memory of what was asked before. Users who want to refine a result must re-state the entire query including the table name, filters, and columns. There is no mechanism on either the server or the client to pass prior turn context, and no UI to indicate whether context is active or to reset it.

## Solution Statement
Extend the request contract with two optional fields — `previous_query` and `previous_sql` — that carry the immediately preceding successful turn's natural language question and generated SQL. When present, the LLM prompt includes a clearly delimited "previous turn" block instructing the model to treat the new query as a follow-up that may reference the previous question/SQL.

On the client, track the last successful `(query, sql)` pair in module state, send it on the next request, and render a "Continuing from: '{query}'" label with a "Clear context" button in the query section. The context is reset (a) when the user clicks "Clear context", and (b) whenever a file upload succeeds. Failed queries never update the stored context, so a failed turn cannot poison subsequent queries.

This keeps the change minimal and backward compatible: the new fields are optional, all existing callers continue to work, and the routing/execution logic in `generate_sql` and the `/api/query` endpoint is unchanged except for threading the two new fields into the prompt builders.

## Relevant Files
Use these files to implement the feature:

- `README.md` - Project overview, structure, and start/stop commands. Read first to understand conventions.
- `app/server/core/data_models.py` - Defines `QueryRequest` (Pydantic). Add optional `previous_query` and `previous_sql` fields here.
- `app/server/core/llm_processor.py` - Contains `generate_sql`, `generate_sql_with_openai`, `generate_sql_with_anthropic`, and `format_schema_for_prompt`. The prompt builders must be extended to include a "previous turn" context block when the new fields are set. `generate_sql` must thread the fields through to the provider functions.
- `app/server/server.py` - Hosts the `POST /api/query` endpoint (`process_natural_language_query`). No signature change needed — it already passes the full `QueryRequest` to `generate_sql` — but confirm the flow and that only successful responses (no `error`) will be used as context by the client.
- `app/server/tests/core/test_llm_processor.py` - Existing unit tests for the LLM processor using mocked clients. Add tests asserting the prompt includes the previous-turn block when context is provided and omits it otherwise.
- `app/client/src/types.d.ts` - TypeScript `QueryRequest` interface. Must mirror the Pydantic model exactly — add `previous_query?: string` and `previous_sql?: string`.
- `app/client/src/api/client.ts` - `api.processQuery` serializes the `QueryRequest`; it already forwards all request fields via `JSON.stringify`, so no change required beyond the type. Verify.
- `app/client/src/main.ts` - Query execution flow (`initializeQueryInput` / `executeQuery`), file upload flow (`handleFileUpload`), and `displayResults`. Add module-level context state, send it with each request, update it on success, render the "Continuing from" label + "Clear context" button, and clear context on upload success.
- `app/client/index.html` - Markup for the query section. Add a container element for the context label + "Clear context" button.
- `app/client/src/style.css` - Existing styles for `.query-controls`, `.secondary-button`, `.query-display`. Add styling for the new context label and clear-context button so they match the existing visual language.
- `.claude/commands/test_e2e.md` - Read to understand how E2E tests are structured and executed.
- `.claude/commands/e2e/test_basic_query.md` - Read as the reference example for authoring a new E2E test file.
- `app_docs/feature-4c768184-model-upgrades.md` - Reference for how the `llm_processor` module and model configs work (matches the conditional docs condition "working with the llm_processor module").

### New Files
- `.claude/commands/e2e/test_conversational_followups.md` - New E2E test file validating the conversational follow-up flow, the context label, the Clear context button, and context clearing on upload. Authored based on `.claude/commands/e2e/test_basic_query.md`.

## Implementation Plan
### Phase 1: Foundation
Extend the shared request contract on both sides. Add the optional `previous_query` and `previous_sql` fields to the server `QueryRequest` Pydantic model and mirror them in the client `QueryRequest` TypeScript interface. These are the shared data structures every other change depends on, so they come first. Because they are optional with no default behavior change, all existing tests and callers remain valid.

### Phase 2: Core Implementation
Update the LLM prompt builders (`generate_sql_with_openai`, `generate_sql_with_anthropic`) to accept the previous-turn context and, when present, inject a clearly delimited block that instructs the model to treat the new query as a follow-up that may reference the prior question and SQL. Update `generate_sql` to pass `request.previous_query` and `request.previous_sql` to whichever provider it routes to. Add unit tests confirming the prompt includes/excludes the context block appropriately.

### Phase 3: Integration
Wire the client. Track the last successful `(query, sql)` pair in module-level state in `main.ts`. Send the stored pair on the next `processQuery` request. On a successful (non-error) response, update the stored context and render the "Continuing from: '{query}'" label plus a "Clear context" button. On a failed query, do not update context. Clicking "Clear context" clears state and hides the label. On a successful file upload, clear the context (label hidden, state reset). Add the label/button container to `index.html` and style it in `style.css`. Author and run the E2E test.

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

### 1. Read reference documentation
- Read `README.md` to confirm project structure and start/stop commands.
- Read `.claude/commands/test_e2e.md` and `.claude/commands/e2e/test_basic_query.md` to understand how E2E test files are authored and executed.
- Read `app_docs/feature-4c768184-model-upgrades.md` for `llm_processor` context.

### 2. Extend the server request model
- In `app/server/core/data_models.py`, add two optional fields to `QueryRequest`:
  - `previous_query: Optional[str] = None  # Prior turn's natural language question, for conversational follow-ups`
  - `previous_sql: Optional[str] = None  # Prior turn's generated SQL, for conversational follow-ups`
- Keep field ordering consistent with the existing style (after `table_name`).

### 3. Extend the LLM prompt builders
- In `app/server/core/llm_processor.py`, add a small helper (no decorators) such as `format_previous_context(previous_query, previous_sql) -> str` that returns an empty string when either value is falsy, or a delimited context block otherwise, e.g.:
  ```
  This is a follow-up question in an ongoing conversation.
  Previous question: "<previous_query>"
  Previous SQL: <previous_sql>

  Treat the new query below as a follow-up that may reference the previous question or its results (e.g. "filter that by ...", "show that as percentages"). Reuse the same tables/columns from the previous SQL unless the new query clearly asks otherwise.
  ```
- Update `generate_sql_with_openai(query_text, schema_info, previous_query=None, previous_sql=None)` and `generate_sql_with_anthropic(query_text, schema_info, previous_query=None, previous_sql=None)` to insert this block into the prompt (between the schema description and the "Convert this natural language query to SQL" instruction) when context is present. Keep the existing rules list intact.
- Update `generate_sql(request, schema_info)` to pass `request.previous_query` and `request.previous_sql` to whichever provider function it calls (both the API-key-priority path and the `request.llm_provider` fallback path).
- Keep all changes backward compatible: default arguments preserve existing behavior.

### 4. Add/adjust server unit tests
- In `app/server/tests/core/test_llm_processor.py`, add tests that:
  - Call `generate_sql_with_openai` (mocked client) with `previous_query`/`previous_sql` set and assert the prompt string passed to the mocked client contains the previous question and previous SQL.
  - Call it without context and assert the prompt does NOT contain the "follow-up" block marker.
  - Add an equivalent test for the Anthropic path.
  - Add a `generate_sql` test asserting the previous-turn values are forwarded to the provider function (assert on the mocked call args).
- Reuse the existing mocking style (`unittest.mock.patch` on `core.llm_processor.OpenAI` / `Anthropic`).

### 5. Mirror the request type on the client
- In `app/client/src/types.d.ts`, add to the `QueryRequest` interface:
  - `previous_query?: string;`
  - `previous_sql?: string;`
- Confirm `app/client/src/api/client.ts` `processQuery` already forwards all fields via `JSON.stringify(request)` (no change expected).

### 6. Add the context label markup
- In `app/client/index.html`, inside `#query-section` (below `.query-controls`), add a hidden container:
  ```html
  <div id="context-indicator" class="context-indicator" style="display: none;">
    <span id="context-label" class="context-label"></span>
    <button id="clear-context-button" class="clear-context-button secondary-button">Clear context</button>
  </div>
  ```

### 7. Implement client context state and wiring in main.ts
- Add module-level state near the top of `main.ts`:
  ```ts
  let previousQuery: string | null = null;
  let previousSql: string | null = null;
  ```
- Add helper functions `updateContextIndicator()` (shows/hides `#context-indicator` and sets `#context-label` text to `Continuing from: '${previousQuery}'`) and `clearConversationContext()` (nulls the state and calls `updateContextIndicator()`).
- In `executeQuery` (in `initializeQueryInput`), include the stored context in the request:
  ```ts
  const response = await api.processQuery({
    query,
    llm_provider: 'openai',
    previous_query: previousQuery ?? undefined,
    previous_sql: previousSql ?? undefined,
  });
  ```
- After a successful response (no `response.error`), set `previousQuery = query; previousSql = response.sql;` and call `updateContextIndicator()`. On error (`displayError` path), do NOT modify context.
- Wire the `#clear-context-button` click handler (in a new `initializeClearContextButton()` called from `DOMContentLoaded`) to call `clearConversationContext()`.
- In `handleFileUpload`, on successful upload (`displayUploadSuccess` branch), call `clearConversationContext()` so a new dataset starts standalone.

### 8. Style the context indicator
- In `app/client/src/style.css`, add `.context-indicator` (flex row, small gap, muted small text, margin below query controls), `.context-label` (small, muted/italic), and `.clear-context-button` (small secondary button; reuse existing `.secondary-button` sizing conventions). Match the existing visual language used by `.query-controls` and `.query-display`.

### 9. Create the E2E test file
- Create `.claude/commands/e2e/test_conversational_followups.md` modeled on `.claude/commands/e2e/test_basic_query.md`. It should include the minimal steps to validate the feature:
  1. Navigate to the Application URL and load the "Users Data" sample (via Upload modal) so a `users` table with a city-like column exists (verify available columns; if no city column, use a filter on an existing column such as an id/name value).
  2. Run "show all users"; verify results and SQL appear.
  3. Verify the "Continuing from: 'show all users'" label and "Clear context" button are visible. Take a screenshot.
  4. Run a follow-up like "filter that by city = 'New York'" (or an existing-column filter); verify the generated SQL references the `users` table without the query re-specifying it. Take a screenshot of the SQL.
  5. Click "Clear context"; verify the label disappears.
  6. Re-open the Upload modal, load another sample dataset; verify the context label is cleared/absent afterward. Take a screenshot.
- Keep steps minimal and include screenshots proving the label, follow-up SQL, and cleared state.

### 10. Run all validation commands
- Execute every command in the `Validation Commands` section and ensure they pass with zero regressions, including the E2E test.

## Testing Strategy
### Unit Tests
- **Prompt inclusion (OpenAI & Anthropic):** With `previous_query`/`previous_sql` set, the generated prompt contains the previous question text and previous SQL, plus the follow-up instruction marker.
- **Prompt exclusion:** Without context, the prompt omits the follow-up block (assert the marker string is absent).
- **Routing pass-through:** `generate_sql` forwards `request.previous_query`/`request.previous_sql` to the selected provider function (assert on mocked call args).
- **Backward compatibility:** Existing `generate_sql_with_openai`/`generate_sql_with_anthropic`/`generate_sql` tests still pass unchanged (default args preserve behavior).

### Edge Cases
- Only one of `previous_query` / `previous_sql` present (e.g. missing SQL) → treat as no context (helper returns empty block); no crash.
- Empty-string context values → treated as no context.
- Failed query response (`response.error` set) → client does not update stored context; the next query uses the prior valid context (or standalone if none).
- File upload success → context cleared even if a prior successful query existed.
- Very long previous query/SQL → still rendered in the label (may be visually truncated via CSS) and sent to the server without error.
- First-ever query (no prior turn) → `previous_query`/`previous_sql` omitted; behaves exactly as today.

## Acceptance Criteria
1. Running "show all users" then "filter that by city = 'New York'" produces correct SQL for the second query that references the `users` table without re-specifying it (via the carried-forward `previous_query`/`previous_sql`).
2. A "Continuing from: '{query}'" label is visible in the query section whenever conversational context is active.
3. Clicking "Clear context" removes the label and the next query is sent standalone (no `previous_query`/`previous_sql`).
4. A failed query does not update or carry forward context; the stored context reflects only the last successful turn.
5. A successful CSV/JSON upload clears any existing context (label hidden, state reset).
6. The new `previous_query`/`previous_sql` fields are optional and backward compatible — all existing server tests and the frontend build pass with zero regressions.

## Validation Commands
Execute every command to validate the feature works correctly with zero regressions.

- `cd app/server && uv run pytest` - Run server tests (including new LLM processor tests) to validate the feature with zero regressions.
- `cd app/server && uv run pytest tests/core/test_llm_processor.py -v` - Focused run of the LLM processor tests for the new context behavior.
- `cd app/client && bun tsc --noEmit` - Type-check the client, confirming the `QueryRequest` interface and `main.ts` changes are type-correct.
- `cd app/client && bun run build` - Build the frontend to confirm no build regressions.
- Read `.claude/commands/test_e2e.md`, then read and execute your new E2E `.claude/commands/e2e/test_conversational_followups.md` test file to validate this functionality works end-to-end (start the app first per README, e.g. `./scripts/start.sh`).

## Notes
- No new libraries are required; the change reuses the existing FastAPI/Pydantic and Vite/TypeScript stacks.
- Keep the implementation decorator-free per project conventions; use a plain helper function for the previous-context prompt block.
- The server already returns `error` on failed queries (it does not raise a 500 to the client for query failures), so the client's "only carry forward on success" rule is simply `if (!response.error)`.
- Context is intentionally kept to a single prior turn (last query + last SQL) per the issue scope, not a full multi-turn history. A future enhancement could maintain a bounded conversation history if deeper multi-step reasoning is desired.
- `previous_sql` is generated server-side SQL (not user free-text) and is only inserted into the prompt, never executed as-is for the follow-up; the follow-up SQL is regenerated and still passes through the existing `execute_sql_safely` / SQL injection protection layer.
