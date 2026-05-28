# Feature: Conversational Follow-ups

## Metadata
issue_number: `d5bcc5c6`
adw_id: `d5bcc5c6`
issue_json: `{"number":44,"title":"2. Conversational Follow-ups","body":"After running a query, the next query automatically includes the previous question + generated SQL as context. The LLM can reference prior results to handle follow-ups like \"now filter that by city\" or \"show that as percentages instead.\" A \"Clear context\" button resets to standalone mode."}`

## Feature Description
Add a single-turn conversational context to the Natural Language SQL Interface. After a query succeeds, the application keeps the previous natural language query and the SQL the LLM produced for it, and sends both back as context with the next query. This lets users phrase follow-up questions naturally ("filter that by city = 'New York'", "show that as percentages instead", "now group it by month") without re-specifying the table or restating the original question. A visible "Continuing from: '<previous query>'" label appears whenever context is active, and a "Clear context" button resets the input to standalone mode. Context is cleared automatically when a query fails or when the user uploads a new CSV/JSON/JSONL file. Only the *most recent* successful (query, SQL) pair is carried forward — this is single-turn follow-up support, not multi-turn chat memory.

## User Story
As a user querying my data in natural language
I want my follow-up questions to inherit the context of the previous query
So that I can iteratively refine results ("now filter by city", "show as percentages") without restating the table name or original question every time.

## Problem Statement
Today every query in this app is independent. The LLM only sees the current natural language query and the full database schema. There is no memory of what the user just asked. A natural follow-up like "now filter that by city" has no referent — the LLM does not know what "that" was, what table to use, what the previous SELECT projected, or how to interpret pronouns like "those rows" or "the same data". Users are forced to repeat themselves ("Show all users in the users table filtered by city = 'New York'") which kills the conversational ergonomics that a natural language interface is supposed to provide.

## Solution Statement
Carry forward exactly one (previous_query, previous_sql) pair between requests:

- **Server**: Extend `QueryRequest` with two optional fields, `previous_query: Optional[str]` and `previous_sql: Optional[str]`. When both are present, the LLM prompt (both OpenAI and Anthropic paths) gets an extra `Previous turn` block that shows the prior natural language question and the SQL the model produced, followed by an instruction that the new query may reference it. The schema block stays as-is so the LLM can still ground SQL in real tables/columns.
- **Client**: Track the last successful `{ query, sql }` pair in module-scope state. Send both fields on the next `/api/query` call. Render a small "Continuing from: '<previous query>'" pill above the input whenever context is active, with a "Clear context" button that wipes the pair and hides the pill. Failed queries do not update the stored pair. Uploading a file clears the pair.

This is a minimal, additive change: the existing standalone-query path is preserved (both `previous_*` fields default to `None`), and there is zero impact on any request that does not opt in.

## Relevant Files
Use these files to implement the feature:

### Backend
- `app/server/core/data_models.py` — Defines `QueryRequest`. Add the two optional context fields here. The Pydantic model is the contract the client must mirror.
- `app/server/core/llm_processor.py` — Both `generate_sql_with_openai` and `generate_sql_with_anthropic` build the prompt. Both need to accept the previous_query / previous_sql context and inject a "Previous turn" section into the prompt when present. The top-level `generate_sql(request, schema_info)` router needs to pass `request.previous_query` and `request.previous_sql` through to whichever provider it dispatches to.
- `app/server/server.py` — `process_natural_language_query` already passes the whole `QueryRequest` into `generate_sql`. With the routing change above, no edits are needed beyond confirming the request flows through; verify there is nothing that strips unknown fields.
- `app/server/tests/core/test_llm_processor.py` — Existing unit tests mock OpenAI/Anthropic clients and assert on prompt construction. Add tests covering the new `Previous turn` block: present when both fields are set, absent when either is missing, and propagated through `generate_sql(...)`.
- `app/server/tests/test_sql_injection.py` — Confirm the new fields cannot be used to bypass SQL validation. The previous_sql is *only* used inside the LLM prompt — it is never executed and never concatenated into a query string. Add a regression test that proves a malicious `previous_sql` input does not change the validation behavior of the actual SQL the LLM emits (or, more simply, that the field is treated as plain text inside the prompt and the new SQL still passes through `validate_sql_query`).

### Frontend
- `app/client/src/types.d.ts` — Mirror the backend `QueryRequest` change: add `previous_query?: string` and `previous_sql?: string`.
- `app/client/src/api/client.ts` — `api.processQuery` already forwards the `QueryRequest` body verbatim, so no edits should be needed once the TS interface is updated. Verify.
- `app/client/src/main.ts` — Owns the query input UI, the executeQuery flow, displayResults, displayError, handleFileUpload. Add module-scope state for the last `(query, sql)` pair. On successful query, store the pair. On failure, do *not* update it. On file upload, clear it. Wire the new "Continuing from" pill + "Clear context" button. Send `previous_query` and `previous_sql` in the next request body.
- `app/client/index.html` — Add the markup for the "Continuing from" pill and "Clear context" button above the query input, hidden by default (CSS `display: none`).
- `app/client/src/style.css` — Add styles for the new pill (small, subtle, with a close-style button). Match the existing visual language — see `.success-message` and `.error-message` for reference patterns.

### E2E Test
- `.claude/commands/test_e2e.md` — Read to understand how E2E tests are structured and executed via Playwright MCP.
- `.claude/commands/e2e/test_basic_query.md` — Read as a template for the structure (User Story, Test Steps, Success Criteria) of a new E2E file.

### New Files
- `specs/issue-d5bcc5c6-adw-d5bcc5c6-sdlc_planner-conversational-follow-ups.md` — This plan.
- `.claude/commands/e2e/test_conversational_followups.md` — New E2E test that exercises the follow-up flow end-to-end (run a query → see "Continuing from" label → run a follow-up → confirm SQL references the table from the first query → click "Clear context" → confirm label disappears).

## Implementation Plan

### Phase 1: Foundation (Server Contract)
Extend the Pydantic request model with the two optional context fields. This is the contract everything else hangs off of. Once `QueryRequest` accepts the fields, the server endpoint already passes the whole request through and the LLM router can read them.

### Phase 2: Core Implementation (LLM Prompt Wiring)
Thread `previous_query` and `previous_sql` from the request through `generate_sql(...)` into both `generate_sql_with_openai` and `generate_sql_with_anthropic`. Each provider builds a `Previous turn:` block that appears between the schema description and the new question. The block only renders when *both* fields are present and non-empty. The instruction text added to the prompt makes it explicit that the new query may reference the previous one ("the user's new query may be a follow-up that refers to the previous turn — interpret pronouns like 'that' / 'those' / 'them' in light of the previous query and SQL").

### Phase 3: Frontend State + UI
Add module-scope state in `main.ts` to hold the last successful `(query, sql)` pair. Update `executeQuery` to send those fields and, on success, update the pair from the response. On failure, leave the pair untouched. On `handleFileUpload` success, clear the pair. Add a "Continuing from" pill in `index.html`, hidden by default. When the pair is set, render the truncated previous query inside it and show the pill; when cleared (manually or otherwise), hide it. Wire a "Clear context" button on the pill that resets the state.

### Phase 4: Integration & Validation
Add unit tests for the LLM prompt construction. Add an E2E Playwright test that proves the full loop works against a running app. Run all validation commands to confirm no regressions.

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

### Step 1: Extend `QueryRequest` in `app/server/core/data_models.py`
- Add two optional fields:
  - `previous_query: Optional[str] = Field(default=None, description="Previous natural language query for follow-up context")`
  - `previous_sql: Optional[str] = Field(default=None, description="SQL generated for the previous query")`
- Place them after the existing `table_name` field to keep grouping clean.
- Do not change any defaults or rename any existing fields.

### Step 2: Update LLM prompt builders in `app/server/core/llm_processor.py`
- Add a small helper `format_previous_turn(previous_query: Optional[str], previous_sql: Optional[str]) -> str` that returns an empty string when either field is missing/blank, and otherwise returns:
  ```
  Previous turn (the user's last interaction in this session):
  - Previous question: "<previous_query>"
  - Previous SQL: <previous_sql>

  The user's new query may be a follow-up that refers to the previous turn. Interpret references like "that", "those rows", "the same data", "now filter by ...", "show that as ..." in light of the previous question and SQL. If the new query is clearly standalone, ignore the previous turn.
  ```
- Update `generate_sql_with_openai(query_text, schema_info, previous_query=None, previous_sql=None)`:
  - Add `previous_query` and `previous_sql` as keyword args with default `None` (preserves existing callers and tests).
  - Insert the `format_previous_turn(...)` output between the schema description and the `Convert this natural language query to SQL: ...` line in the prompt. If empty, nothing is inserted.
- Apply the same change to `generate_sql_with_anthropic(...)`.
- Update `generate_sql(request, schema_info)` to forward `request.previous_query` and `request.previous_sql` into whichever provider function it dispatches to.

### Step 3: Update `app/server/tests/core/test_llm_processor.py`
- Add a test `test_generate_sql_with_openai_includes_previous_turn` that mocks the OpenAI client, calls `generate_sql_with_openai(query, schema, previous_query="show all users", previous_sql="SELECT * FROM users")`, and asserts the prompt passed to `chat.completions.create` contains the literal strings `Previous turn`, `show all users`, and `SELECT * FROM users`.
- Add a mirror test `test_generate_sql_with_anthropic_includes_previous_turn` for the Anthropic path.
- Add `test_generate_sql_omits_previous_turn_when_missing` — calling either provider with `previous_query=None` or `previous_sql=None` (or empty strings) must NOT include `Previous turn` in the prompt.
- Add `test_generate_sql_router_forwards_previous_context` — call `generate_sql(QueryRequest(query="...", previous_query="q", previous_sql="SELECT 1"), schema_info)` with OpenAI mocked, and assert the mock received both `previous_query="q"` and `previous_sql="SELECT 1"`.
- Re-run the file: `cd app/server && uv run pytest tests/core/test_llm_processor.py -v` and confirm all tests pass.

### Step 4: Add a SQL-injection regression test in `app/server/tests/test_sql_injection.py`
- Add a test `test_previous_sql_field_is_inert` that sends a `QueryRequest` whose `previous_sql` contains a dangerous payload (e.g. `"DROP TABLE users; --"`), mocks the LLM to return a benign `SELECT * FROM users`, and verifies:
  1. `validate_sql_query` is still called on the LLM's returned SQL (not on `previous_sql`).
  2. No SQL execution path receives `previous_sql` directly.
  - The simplest realization: assert that the value of `previous_sql` does not appear anywhere in the executed SQL string, and that the request still returns a successful response.

### Step 5: Mirror the type contract on the client — `app/client/src/types.d.ts`
- Extend `QueryRequest`:
  ```ts
  interface QueryRequest {
    query: string;
    llm_provider: "openai" | "anthropic";
    table_name?: string;
    previous_query?: string;
    previous_sql?: string;
  }
  ```
- No change needed in `app/client/src/api/client.ts` — it already `JSON.stringify`s the whole request object.

### Step 6: Add UI markup in `app/client/index.html`
- Above the `<textarea id="query-input">` inside `<section id="query-section">`, add:
  ```html
  <div id="context-pill" class="context-pill" style="display: none;">
    <span class="context-pill-label">Continuing from: </span>
    <span id="context-pill-query" class="context-pill-query"></span>
    <button id="clear-context-button" class="clear-context-button" title="Clear context">&times;</button>
  </div>
  ```
- Keep the existing `query-controls` block unchanged.

### Step 7: Style the context pill in `app/client/src/style.css`
- Add a `.context-pill` rule: subtle background (use an existing accent variable like the success-message tinted color), small padding, rounded corners, inline-flex layout, displayed above the textarea with a small bottom margin.
- Add `.context-pill-query` rule: italic, truncated with `max-width` + `overflow: hidden; text-overflow: ellipsis; white-space: nowrap;` so very long previous queries don't blow up the layout.
- Add `.clear-context-button` rule: small `×` button, no border, hover state matches the existing `.close-modal` style.
- Do not invent new color tokens — reuse the existing CSS variables.

### Step 8: Add context state + wiring in `app/client/src/main.ts`
- At module top scope (after the imports, before `DOMContentLoaded`), add:
  ```ts
  let previousQuery: string | null = null;
  let previousSql: string | null = null;
  ```
- Add a `setContext(query: string | null, sql: string | null)` helper that:
  - Updates the two module-scope variables.
  - If both are non-null/non-empty, sets `#context-pill-query` text to the truncated previous query (truncate to ~80 chars with an ellipsis) and shows `#context-pill`.
  - Otherwise hides `#context-pill`.
- Inside `initializeQueryInput`, in the `executeQuery` function:
  - When building the request, include `previous_query: previousQuery ?? undefined` and `previous_sql: previousSql ?? undefined`.
  - In the `try` branch, after `displayResults(response, query)`, call `setContext(query, response.sql)` — only when `response.error` is falsy and `response.sql` is non-empty.
  - In the `catch` branch and when `response.error` is truthy, do NOT update the context (failed queries do not carry forward).
- In `displayError`, do not touch the context.
- In `handleFileUpload`'s success branch (after `displayUploadSuccess(response)`), call `setContext(null, null)`.
- Add a new `initializeClearContextButton()` function that wires `#clear-context-button` click to `setContext(null, null)`, and call it from `DOMContentLoaded`.
- Call `setContext(null, null)` once on startup to ensure the pill is hidden.

### Step 9: Create the E2E test file `.claude/commands/e2e/test_conversational_followups.md`
- Read `.claude/commands/test_e2e.md` and `.claude/commands/e2e/test_basic_query.md` first to match structure and tone.
- Use the same sections: **User Story**, **Test Steps**, **Success Criteria**.
- The steps should cover:
  1. Navigate to the app and screenshot the initial state.
  2. **Verify** the "Continuing from" pill is NOT visible at start.
  3. Load the Users sample data via the Upload modal.
  4. Enter "Show me all users" and click Query.
  5. **Verify** the results table appears and the SQL contains `users`.
  6. Screenshot the results.
  7. **Verify** the "Continuing from: 'Show me all users'" pill is now visible above the input.
  8. Enter the follow-up "filter that by city" and click Query. (Note: any city value the LLM picks is fine — we are not asserting the exact city literal, only that the new SQL references the `users` table and has a WHERE clause referencing `city`.)
  9. **Verify** the generated SQL contains `users` AND `WHERE` AND `city` (case-insensitive).
  10. Screenshot the follow-up SQL and results.
  11. Click the "×" / Clear context button on the pill.
  12. **Verify** the pill is hidden again.
  13. Screenshot the final state.
- Match the screenshot count and naming convention used by `test_basic_query.md`.

### Step 10: Run all validation commands
- Run every command listed in the **Validation Commands** section below. All must succeed with zero regressions and zero errors before the feature is considered complete.

## Testing Strategy

### Unit Tests
- **Prompt construction (OpenAI)**: `Previous turn` block is included only when both `previous_query` and `previous_sql` are present and non-empty.
- **Prompt construction (Anthropic)**: same, on the Anthropic path.
- **Empty / missing previous fields**: prompts produced when previous fields are `None` or empty strings are byte-for-byte identical to today's prompts (regression-protect the standalone path).
- **Router forwarding**: `generate_sql(QueryRequest(..., previous_query=..., previous_sql=...), schema_info)` forwards both fields into the chosen provider function.
- **SQL injection inertness**: a malicious `previous_sql` value never reaches `execute_sql_safely` and never becomes part of the executed SQL.

### Edge Cases
- Follow-up query when previous query *failed* — pair must not have been stored, so request is standalone. Already covered by Step 8 wiring; the E2E + unit logic protect this.
- Follow-up query after the previous *table was deleted* — the LLM may produce bad SQL referencing a missing table, the user sees the error, the failed query does not update context, so the previous (valid) context is still there. Acceptable behavior; no special handling required.
- Very long previous query — truncated to ~80 chars in the pill so it does not overflow.
- New CSV uploaded mid-session — context cleared (acceptance criterion #5).
- User manually clicks Clear context — pill hidden, next query is standalone (acceptance criterion #3).
- Both `previous_query` and `previous_sql` are sent but one is an empty string — prompt builder treats this as "no context" (defensive; the client should never send this, but the server guards it).

## Acceptance Criteria
Aligns with the issue body:

1. ✅ Running "show all users" then "filter that by city = 'New York'" produces correct SQL on the second query *without* re-specifying the `users` table. Verified by the E2E test (Step 9 SQL assertions).
2. ✅ A "Continuing from: '<query>'" label is visible while context is active. Verified by E2E test step 7.
3. ✅ Clicking "Clear context" removes the label; the next query is sent without previous_query/previous_sql. Verified by E2E test steps 11–12 + manual inspection of the network request.
4. ✅ Failed queries do not carry forward as context. Enforced by the conditional `setContext` call in `executeQuery` (only on success) and protected by code review.
5. ✅ Uploading a new CSV clears existing context. Enforced by the `setContext(null, null)` call in `handleFileUpload` success branch.

Additionally:
6. ✅ All existing server unit tests continue to pass (`cd app/server && uv run pytest`).
7. ✅ The frontend type-checks (`cd app/client && bun tsc --noEmit`) and builds (`cd app/client && bun run build`).
8. ✅ Existing E2E tests (`test_basic_query`, `test_complex_query`, etc.) still pass — they never set previous_query/previous_sql, so they exercise the unchanged standalone path.

## Validation Commands
Execute every command to validate the feature works correctly with zero regressions.

- `cd app/server && uv run pytest -v` — Run the full server test suite (includes the new prompt and SQL-injection tests). All tests must pass.
- `cd app/server && uv run pytest tests/core/test_llm_processor.py -v` — Targeted run of the new LLM prompt tests for fast iteration.
- `cd app/client && bun tsc --noEmit` — Type-check the client; the new `previous_query` / `previous_sql` fields on `QueryRequest` must be accepted everywhere they are passed.
- `cd app/client && bun run build` — Production build of the client. Must succeed with zero errors.
- Start the app via `./scripts/start.sh` (or whatever the project's standard start path is) and manually verify:
  1. Run "show me all users" against the Users sample data — pill appears.
  2. Run "filter that by city = 'New York'" — second SQL references `users` without restating it, results render.
  3. Click Clear context — pill disappears, next query is standalone.
  4. Cause a failure (e.g., "DELETE all rows" — gets rejected) — context from the previous successful query is preserved.
  5. Upload a new sample dataset — pill disappears.
- Read `.claude/commands/test_e2e.md`, then read and execute the new `.claude/commands/e2e/test_conversational_followups.md` test file to validate the functionality end-to-end with Playwright. All steps must pass and screenshots must be captured.

## Notes
- **No new dependencies.** No `uv add` calls and no new npm packages are required for this feature.
- **Single-turn only by design.** This implementation keeps exactly one previous (query, SQL) pair. Multi-turn chat memory (full transcript) is intentionally out of scope — it adds prompt-size pressure, complicates the UI, and was not in the issue.
- **Cost considerations.** Including the previous turn adds ~50–150 tokens to each follow-up prompt. This is acceptable for a single-turn carry; if multi-turn is added later, consider truncation or summarization.
- **Why send previous_sql, not just previous_query?** The SQL is the most concrete grounding signal the LLM has — it disambiguates table names, joins, projections, and filter columns that the natural language alone leaves ambiguous. Sending both gives the model the best chance to interpret "that" and "those rows" correctly.
- **Privacy / safety.** `previous_sql` is treated as untrusted text inside the LLM prompt. It is never executed and never concatenated into the actual query string. The new SQL the LLM emits still goes through the same `validate_sql_query` pipeline as today.
- **Future extension hook.** If multi-turn is later requested, the natural extension is to change `previous_query: Optional[str]` to `history: list[TurnContext]` on `QueryRequest`. The current single-field design is forward-compatible: adding `history` later won't break clients that still send `previous_query`/`previous_sql`.
