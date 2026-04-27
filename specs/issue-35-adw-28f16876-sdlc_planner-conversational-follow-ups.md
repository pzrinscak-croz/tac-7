# Feature: Conversational Follow-ups

## Metadata
issue_number: `35`
adw_id: `28f16876`
issue_json: `{"number":35,"title":"Conversational Follow-ups","body":"/feature\n\nadw_sdlc_iso\n\nmodel_set heavy\n\nAfter running a query, the next query automatically includes the previous question + generated SQL as context. The LLM can reference prior results to handle follow-ups like \"now filter that by city\" or \"show that as percentages instead.\" A \"Clear context\" button resets to standalone mode.\n\n**Scope:**\n- Server: Add optional previous_query and previous_sql fields to QueryRequest, include them in the LLM prompt\n- Client: Track last query/SQL pair, send with next request, show a small \"continuing from...\" label\n\n**Acceptance criteria:**\n1. Run \"show all users\", then \"filter that by city = 'New York'\" -- the second query produces correct SQL without re-specifying the table\n2. A \"Continuing from: '{query}'\" label is visible when context is active\n3. Clicking \"Clear context\" removes the label; the next query is standalone\n4. Failed queries do not carry forward as context\n5. Uploading a new CSV clears existing context"}`

## Feature Description
Add conversational follow-up support to the Natural Language SQL Interface. After a successful query, the user's previous natural-language question and the SQL the LLM produced for it are automatically passed as context with the next query. This enables users to issue short follow-ups such as "filter that by city = 'New York'" or "show that as percentages instead" without re-specifying the table or restating prior context. A small "Continuing from: '{previous query}'" label appears in the query section whenever context is active, and a "Clear context" button next to that label resets the conversation to standalone mode. Context is also automatically cleared when a new CSV/JSON/JSONL file is uploaded, and failed queries do not carry forward.

## User Story
As a data analyst exploring a newly uploaded dataset
I want my next natural-language question to automatically build on the previous question and its generated SQL
So that I can iterate on a query (filter, group, aggregate, reformat) using short conversational follow-ups instead of restating the entire question every time.

## Problem Statement
Today, every query against the application is fully standalone. The LLM has the database schema but no memory of the previous question or the SQL it produced. This means the user must restate the table name, prior filters, and other context every time they want to refine a result. Common analytical workflows ("show me X" -> "now filter that by Y" -> "now group by Z") require the user to do most of the work the LLM should be doing for them, and short follow-up phrasings like "now filter that by city" cannot succeed because the LLM has no way to know what "that" refers to.

## Solution Statement
Extend the `/api/query` request contract with two optional fields, `previous_query` and `previous_sql`, and inject them into the LLM prompt as a "Previous turn" section when present. On the client, store the last *successful* `(query, sql)` pair as conversation context. On every subsequent query the client sends those two fields along with the new natural-language question. A small label "Continuing from: '{previous_query}'" is rendered just above the query input when context is active, with a sibling "Clear context" button that wipes the stored pair and hides the label. Failed responses (server returns `error`) never replace the existing context, and the upload handler explicitly clears the context whenever a file upload succeeds. The change is fully backwards compatible: when the client sends no context fields, server behavior is identical to today.

## Relevant Files
Use these files to implement the feature:

- `app/server/core/data_models.py` - Defines `QueryRequest`. Add the two optional context fields here (`previous_query`, `previous_sql`).
- `app/server/core/llm_processor.py` - Contains `generate_sql_with_openai`, `generate_sql_with_anthropic`, and the routing function `generate_sql`. The OpenAI/Anthropic prompts are constructed here and must be extended with a "Previous turn" section. The signature change must propagate through `generate_sql` -> the per-provider helpers.
- `app/server/server.py` - The `/api/query` endpoint at lines 116-153 calls `generate_sql(request, schema_info)`. The request object already carries the new fields once `data_models.py` is updated, so this file needs minimal changes; verify no extra plumbing is required.
- `app/server/tests/core/test_llm_processor.py` - Existing unit tests for the LLM layer. Add new tests covering the context injection (prompt contains "Previous turn", per-provider dispatch passes the fields through, no-context behavior is unchanged).
- `app/client/src/types.d.ts` - TypeScript `QueryRequest` interface. Add the two optional fields so the type matches the Pydantic model.
- `app/client/src/api/client.ts` - `api.processQuery` already accepts a `QueryRequest`; verify it transparently forwards the new fields once the type is updated.
- `app/client/src/main.ts` - Where the bulk of the client work happens: track conversation context state, send it with each request, render/hide the "Continuing from..." label, wire up the "Clear context" button, and clear context on successful file uploads.
- `app/client/index.html` - Add the `#context-banner` element (label + Clear context button) inside the query section. Add an Upload modal sample data section if needed (no new sample data required, just verifying placement).
- `app/client/src/style.css` - Add styles for the new `.context-banner`, `.context-banner-label`, and `.clear-context-button` classes consistent with the existing light-sky-blue theme and button conventions.
- `README.md` - Update the Usage section to mention conversational follow-ups and the Clear context button. Update the API Endpoints reference if needed (the endpoint URL doesn't change, but the request body now accepts two new optional fields).
- `.claude/commands/test_e2e.md` - Read this to understand how E2E tests are authored and executed in this repo.
- `.claude/commands/e2e/test_basic_query.md` - Read for the canonical E2E test structure (User Story / Test Steps / Success Criteria, screenshot conventions, language).
- `.claude/commands/e2e/test_complex_query.md` - Second example to mirror screenshot pacing and assertion style.
- `app_docs/feature-4c768184-model-upgrades.md` - Read because this feature modifies the LLM prompt construction in `llm_processor.py`.

### New Files
- `.claude/commands/e2e/test_conversational_follow_ups.md` - New E2E test that uploads sample users data, issues an initial query, then a follow-up query (e.g. "filter that by city"), verifies the "Continuing from..." banner appears, verifies the second SQL references the same table without restating it, then clicks "Clear context" and verifies the banner disappears and the next query is standalone.

## Implementation Plan

### Phase 1: Foundation
Update the request/response contracts on both sides so the new optional fields exist end-to-end before changing any behavior. This means: extend Pydantic `QueryRequest`, mirror the change in the TypeScript `QueryRequest` interface, and verify the existing `api.processQuery` and FastAPI handler transparently round-trip the new fields. After this phase, no behavior changes; the system simply accepts and ignores the new fields.

### Phase 2: Core Implementation
Wire the new fields into the LLM prompt. Update `generate_sql`, `generate_sql_with_openai`, and `generate_sql_with_anthropic` so they take optional `previous_query` and `previous_sql`, and prepend a "Previous turn" section to the prompt when both are present. On the client, introduce a small `conversationContext` module-level object holding `{ previousQuery, previousSql }`. After every *successful* query response (no `response.error`, no thrown exception), store the pair. Send the pair on every subsequent query. Add the "Continuing from..." banner element to `index.html`, the `.context-banner` styles to `style.css`, and the show/hide logic + Clear context wiring in `main.ts`.

### Phase 3: Integration
Connect the context lifecycle to other application events. Hook `handleFileUpload` so that on success it clears `conversationContext` and hides the banner (acceptance criterion 5). Ensure failed queries (response with `error` field, or thrown exception in the `catch` block) do NOT update `conversationContext` (acceptance criterion 4). Add server-side tests, write the new E2E test file, update README.md, and run the full validation suite.

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

### Step 1: Read prerequisite documentation
- Read `README.md` for project structure and start/stop commands.
- Read `app_docs/feature-4c768184-model-upgrades.md` because this feature modifies prompt construction in `llm_processor.py`.
- Read `.claude/commands/test_e2e.md` and `.claude/commands/e2e/test_basic_query.md` and `.claude/commands/e2e/test_complex_query.md` to understand the E2E test conventions before drafting the new test file.

### Step 2: Extend the server `QueryRequest` model
- Edit `app/server/core/data_models.py`.
- Add two new optional fields to `QueryRequest` immediately after the existing `table_name` field:
  - `previous_query: Optional[str] = None  # Previous natural language query for follow-up context`
  - `previous_sql: Optional[str] = None    # SQL generated for the previous query`
- Do not change defaults or rename existing fields. Both new fields must default to `None` so existing clients that don't send them continue to work.

### Step 3: Inject context into the LLM prompt
- Edit `app/server/core/llm_processor.py`.
- Update both `generate_sql_with_openai(query_text, schema_info)` and `generate_sql_with_anthropic(query_text, schema_info)` to accept two new optional keyword arguments: `previous_query: Optional[str] = None` and `previous_sql: Optional[str] = None`.
- In each function, just before the `Convert this natural language query to SQL: "{query_text}"` line, conditionally insert a "Previous turn" block if both `previous_query` and `previous_sql` are truthy, formatted exactly like:
  ```
  Previous turn (use as conversational context for the new question):
  - Previous question: "{previous_query}"
  - Previous SQL: {previous_sql}

  When the new question references the previous result with words like "that", "those", "it", "now filter...", "now group by...", "show that as...", interpret it as a refinement of the previous SQL. Do not re-explain or repeat the previous SQL; produce a single new SQL statement that satisfies the new question.

  ```
  (If only one of the two is present, do NOT inject anything - context requires both.)
- Update `generate_sql(request, schema_info)` so it forwards `request.previous_query` and `request.previous_sql` to whichever provider helper it dispatches to. Both call sites in `generate_sql` (the API-key-priority branch and the request-preference branch) must forward the fields.
- Do not change any of the existing rules in the prompt; only prepend the "Previous turn" block when active.
- Keep the existing `Optional` import; add it to the `from typing import` line if not already present.

### Step 4: Add server unit tests for context injection
- Edit `app/server/tests/core/test_llm_processor.py`.
- Add tests in the `TestLLMProcessor` class:
  - `test_generate_sql_with_openai_includes_previous_turn`: mock OpenAI, call `generate_sql_with_openai(...)` with `previous_query="show all users"` and `previous_sql="SELECT * FROM users"`, then assert the captured `messages[1]['content']` contains the strings `"Previous turn"`, `"show all users"`, and `"SELECT * FROM users"`.
  - `test_generate_sql_with_openai_no_previous_turn`: mock OpenAI, call without previous fields, assert the prompt does NOT contain `"Previous turn"`.
  - `test_generate_sql_with_anthropic_includes_previous_turn`: mock Anthropic, same idea as the OpenAI test but reading from `messages` kwarg.
  - `test_generate_sql_with_anthropic_no_previous_turn`: same as the OpenAI no-context test but for Anthropic.
  - `test_generate_sql_routes_previous_fields_to_openai`: with `OPENAI_API_KEY` set, build `QueryRequest(query="...", previous_query="...", previous_sql="...")`, patch `generate_sql_with_openai`, call `generate_sql`, and assert the patched function was called with `previous_query` and `previous_sql` keyword arguments forwarded.
  - `test_generate_sql_routes_previous_fields_to_anthropic`: same as above but with only `ANTHROPIC_API_KEY` set and the Anthropic helper patched.
  - `test_generate_sql_partial_context_ignored`: provide `previous_query` only (or `previous_sql` only) and assert the resulting prompt does NOT contain `"Previous turn"` (both must be set for context to fire).

### Step 5: Update the client `QueryRequest` type
- Edit `app/client/src/types.d.ts`.
- In the `QueryRequest` interface add two optional fields after `table_name`:
  - `previous_query?: string;`
  - `previous_sql?: string;`
- Keep the comment block at the top of the file accurate ("These must match the Pydantic models exactly").

### Step 6: Add the context banner UI to the HTML
- Edit `app/client/index.html`.
- Inside the `#query-section` `<section>`, immediately *above* the `<textarea id="query-input">` element, add:
  ```html
  <div id="context-banner" class="context-banner" style="display: none;">
    <span class="context-banner-label">Continuing from: <em id="context-previous-query"></em></span>
    <button id="clear-context-button" class="clear-context-button" type="button">Clear context</button>
  </div>
  ```
- Do not change any other elements in this section; the banner must appear above the textarea and remain hidden by default.

### Step 7: Style the context banner
- Edit `app/client/src/style.css`.
- Add new rules (placed near the existing `.query-section` / `.query-controls` rules) for:
  - `.context-banner` - flex row, space-between, small vertical padding, subtle background using existing CSS variables (e.g. a light tinted box matching the sky-blue theme), small bottom margin so it sits cleanly above the textarea.
  - `.context-banner-label` - small font size, muted color; the `<em>` inside should be slightly emphasized.
  - `.clear-context-button` - reuse the look of `.secondary-button` (or a smaller text-button variant), do not introduce new colors outside the existing palette.
- Keep the styling minimal and consistent with the existing aesthetic. Do NOT alter unrelated rules.

### Step 8: Implement client-side context state and lifecycle
- Edit `app/client/src/main.ts`.
- At module scope (near the top, where the comment `// Global state` already exists), add:
  ```ts
  // Conversational follow-up context (last successful query + SQL pair)
  let conversationContext: { previousQuery: string; previousSql: string } | null = null;
  ```
- Add two helper functions near the other helpers (e.g. just below `getDownloadIcon`):
  - `function updateContextBanner(): void` - looks up `#context-banner` and `#context-previous-query`. If `conversationContext` is non-null, sets the `<em>`'s `textContent` to `conversationContext.previousQuery` and shows the banner (`display = 'flex'`); otherwise hides the banner (`display = 'none'`).
  - `function clearConversationContext(): void` - sets `conversationContext = null` and calls `updateContextBanner()`.
- In `initializeQueryInput`, modify `executeQuery` so the `api.processQuery({...})` call includes the context fields when present:
  ```ts
  const response = await api.processQuery({
    query,
    llm_provider: 'openai',
    ...(conversationContext ? {
      previous_query: conversationContext.previousQuery,
      previous_sql: conversationContext.previousSql,
    } : {}),
  });
  ```
- Still inside `executeQuery`, after `displayResults(response, query);`, add logic to store context on success. A response is "successful" when there is no thrown exception AND `response.error` is falsy AND `response.sql` is truthy. In that case, set:
  ```ts
  conversationContext = { previousQuery: query, previousSql: response.sql };
  updateContextBanner();
  ```
  If `response.error` is set (server-returned error), do NOT update `conversationContext`. The existing `catch` block must also leave `conversationContext` untouched (do not clear it on a thrown error - the user may have lost network for one second; preserving the prior context is safer and matches "failed queries do not carry forward" without destroying valid prior context).
- Add a new initializer `initializeContextBanner()` invoked from the `DOMContentLoaded` handler (alongside `initializeQueryInput`, etc.). Inside it: look up `#clear-context-button` and attach a `click` listener that calls `clearConversationContext()`. Then call `updateContextBanner()` once to ensure the banner reflects the (initially empty) state.
- In `handleFileUpload`, after a successful upload (the `else` branch where `displayUploadSuccess(response)` is called and before/after `loadDatabaseSchema()`), call `clearConversationContext()` so a new dataset always starts a fresh conversation.

### Step 9: Update README documentation
- Edit `README.md`.
- In the Usage section, add a new bullet under "Query Your Data" describing conversational follow-ups: "After a successful query, follow-up questions like 'now filter that by city' use the previous question and SQL as context. Click 'Clear context' to reset to a standalone query." 
- In the API Endpoints section, add a one-line note that `POST /api/query` accepts optional `previous_query` and `previous_sql` fields for conversational context.

### Step 10: Create the new E2E test file
- Create `.claude/commands/e2e/test_conversational_follow_ups.md` with the structure used in `test_basic_query.md` (`# E2E Test: Conversational Follow-ups`, "User Story", "Test Steps", "Success Criteria").
- The test must:
  1. Navigate to the Application URL and take a screenshot of the initial state.
  2. Verify the `#context-banner` is hidden initially.
  3. Open the upload modal and click the "Users Data" sample button to load the users table (acceptance criteria require a known dataset; using sample data avoids fixture authoring).
  4. Wait for the table to appear in the Available Tables section.
  5. Enter the query "show all users", click Query, and wait for results.
  6. Verify the SQL contains `users` (e.g. assert it matches `SELECT * FROM users` or contains `FROM users`).
  7. Verify the `#context-banner` is now visible and `#context-previous-query` contains "show all users". Screenshot.
  8. Enter "filter that by city = 'New York'", click Query, and wait for results.
  9. Verify the new SQL still references `users` (or `FROM users`), and contains a `WHERE` clause with `city` and `New York`. Screenshot.
  10. Verify the banner now shows the previous query as "filter that by city = 'New York'".
  11. Click the "Clear context" button.
  12. Verify the `#context-banner` is hidden. Screenshot.
  13. Enter a new query "show all users", click Query, and verify the SQL is generated successfully without the context-injected "Previous turn" reference (the request should not have shipped the previous_query/previous_sql fields - this is best validated visually via the missing banner before the click).
  14. Take a final screenshot.
- Success criteria: the banner toggles correctly across the three lifecycle events (after first query, after follow-up, after clear); the second SQL produces a `WHERE city = 'New York'` clause without the user re-specifying `users`; failed-query and upload-clears-context behaviors are noted but not part of the minimal test path; at least 4 screenshots are taken.

### Step 11: Run validation
- Execute every command in the Validation Commands section below, in order, and confirm zero failures and zero regressions.

## Testing Strategy

### Unit Tests
- Server (`tests/core/test_llm_processor.py`): cover both providers and both states (with/without context), plus partial-context-ignored behavior, plus `generate_sql` routing forwarding the new fields. See Step 4 for the concrete list.
- TypeScript types: `bun tsc --noEmit` validates the `QueryRequest` interface change is consistent with all call sites.

### Edge Cases
- Only one of `previous_query` / `previous_sql` is sent: server must NOT inject the "Previous turn" block (covered by `test_generate_sql_partial_context_ignored`).
- Server-side error response (`response.error` set, `sql` empty): client must NOT replace existing `conversationContext` with the failed turn.
- Network/throw error in client: existing `conversationContext` is preserved (the user can retry the same follow-up after a transient failure).
- File upload success: client clears `conversationContext` so the next query has no carry-over from a different dataset.
- Removing a table (existing flow at `removeTable`): out of scope for this issue's acceptance criteria, but note: the conversation context could become stale. Do NOT add proactive clearing on table removal in this iteration; the user can click "Clear context" if needed. Document this in Notes.
- Empty `previous_sql` (e.g. the previous turn returned `sql=""` because of an error): the client never stores an entry with empty `sql`, so this case cannot occur in practice; nevertheless the server's "both must be truthy" guard makes it harmless.
- Backwards compatibility: clients/scripts that POST to `/api/query` without the two new fields continue to work unchanged because both fields default to `None`.

## Acceptance Criteria
1. With sample users data loaded, running "show all users" followed by "filter that by city = 'New York'" produces SQL that references the `users` table and applies a `WHERE city = 'New York'` filter, without the user restating the table name.
2. After a successful query, a "Continuing from: '{previous query}'" label is visible above the query input.
3. Clicking "Clear context" hides the label, removes the stored context, and the next query is sent without `previous_query` / `previous_sql` (verified by it being treated as a fresh standalone query).
4. A query that returns an error response (or throws) does NOT replace the previously stored context. The banner continues to reflect the last *successful* turn.
5. A successful CSV/JSON/JSONL upload clears the conversation context and hides the banner.
6. All existing server tests continue to pass (no regressions in `test_llm_processor.py` or other test files).
7. `bun tsc --noEmit` and `bun run build` succeed without TypeScript errors.
8. The new E2E test file passes when executed.

## Validation Commands
Execute every command to validate the feature works correctly with zero regressions.

- `cd app/server && uv run pytest` - Run server tests to validate the feature works with zero regressions.
- `cd app/server && uv run pytest tests/core/test_llm_processor.py -v` - Specifically verify the new context-injection unit tests pass.
- `cd app/client && bun tsc --noEmit` - Type-check the client to validate the new optional fields on `QueryRequest` are consistent across the codebase.
- `cd app/client && bun run build` - Build the client to validate there are no compile-time errors.
- Read `.claude/commands/test_e2e.md`, then read and execute the new E2E test file `.claude/commands/e2e/test_conversational_follow_ups.md` to validate this functionality works end-to-end.
- Read `.claude/commands/test_e2e.md`, then read and execute `.claude/commands/e2e/test_basic_query.md` to confirm the basic single-query flow continues to work (no regression introduced by the context plumbing).

## Notes
- No new Python or JavaScript dependencies are needed. All changes use existing libraries (`pydantic`, `fastapi`, vanilla TS, existing CSS).
- The "Previous turn" prompt section is intentionally short and instructs the LLM to produce *one* new SQL statement; we do not pass results rows or row counts back into the prompt - that would balloon token usage and isn't required for the stated acceptance criteria. If a future iteration wants schema-aware result-shape context (e.g. column names from prior result), that can be a follow-up feature.
- Context is stored in memory only (a module-level variable in `main.ts`). It is NOT persisted across page reloads. This matches the issue's intent ("a small label, a Clear context button") and avoids storage/PII concerns.
- The "Clear context" button does not currently appear on the screen until at least one successful query has happened (the banner is hidden initially). This is intentional: when there is no context to clear, the button would be noise.
- We deliberately do NOT clear context on *table removal*. A user removing a table that the prior turn referenced is an acceptable failure mode (the next follow-up will fail at the SQL execution step and the user can click "Clear context" themselves). Adding proactive clearing here would require coupling between the table-removal flow and conversation state that the issue does not request.
- The OpenAI and Anthropic prompts are kept in lockstep (same "Previous turn" wording) so behavior does not diverge by provider.
- Backwards compatibility: omitting the two new fields in a `/api/query` POST behaves exactly as before. No version bump or migration is required.
