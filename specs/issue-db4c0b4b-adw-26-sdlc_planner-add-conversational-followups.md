# Feature: Conversational Follow-ups

## Metadata
issue_number: `db4c0b4b`
adw_id: `26`
issue_json: ``

## Feature Description
Add conversational follow-up support to the Natural Language SQL Interface. After running a query, the next query automatically includes the previous question and generated SQL as context, allowing the LLM to handle follow-ups like "now filter that by city" or "show that as percentages instead." A "Clear context" button resets to standalone mode, and context is automatically cleared on failed queries or new CSV uploads.

## User Story
As a data analyst
I want to ask follow-up questions that reference my previous query
So that I can iteratively explore data without re-specifying tables and conditions each time

## Problem Statement
Currently every query is stateless -- each natural language question is sent to the LLM with only the database schema, so users must fully specify their intent every time. This makes iterative data exploration tedious: after running "show all users," the user cannot simply say "filter that by city = 'New York'" because the LLM has no knowledge of the previous query.

## Solution Statement
Track the last successful query/SQL pair on the client and send it as optional `previous_query` and `previous_sql` fields in the `QueryRequest`. The server injects this context into the LLM prompt so the model can resolve references like "that," "those results," etc. The client shows a "Continuing from: '{query}'" label when context is active and provides a "Clear context" button to reset. Failed queries do not update context, and uploading a new file automatically clears it.

## Relevant Files
Use these files to implement the feature:

- `app/server/core/data_models.py` (lines 17-21) -- Add `previous_query` and `previous_sql` optional fields to `QueryRequest`
- `app/server/core/llm_processor.py` (lines 7-126) -- Modify `generate_sql_with_openai()` and `generate_sql_with_anthropic()` to accept and inject conversation context into the prompt; update `generate_sql()` routing function (lines 267-285) to pass context through
- `app/server/server.py` (lines 116-153) -- Pass new fields from request to `generate_sql()`
- `app/client/src/types.d.ts` (lines 13-17) -- Add `previous_query?` and `previous_sql?` to `QueryRequest` interface
- `app/client/src/main.ts` (lines 1-91) -- Add conversation context state, send context with queries, update on success, clear on failure/upload; add UI for "Continuing from" label and "Clear context" button
- `app/client/index.html` (lines 14-29) -- Add context indicator element in the query section
- `app/client/src/style.css` -- Add styles for the context indicator label and clear button
- `app/server/tests/core/test_llm_processor.py` -- Add tests for conversation context in prompt generation
- `app/client/src/api/client.ts` (lines 48-56) -- No changes needed; `processQuery` already sends the full request object
- Read `.claude/commands/test_e2e.md` and `.claude/commands/e2e/test_basic_query.md` to understand how to create the E2E test file
- `app_docs/feature-4c768184-model-upgrades.md` -- Reference for LLM processor patterns

### New Files
- `.claude/commands/e2e/test_conversational_followups.md` -- E2E test for conversational follow-up functionality

## Implementation Plan
### Phase 1: Foundation
Extend the data models on both server and client to support optional conversation context fields (`previous_query`, `previous_sql`). These are optional fields that default to `None`/`undefined`, so existing functionality is unaffected.

### Phase 2: Core Implementation
Modify the LLM prompt construction in `llm_processor.py` to conditionally include conversation context when `previous_query` and `previous_sql` are provided. Update both OpenAI and Anthropic code paths. On the client, add state tracking for the last successful query/SQL pair and wire it into the query submission flow.

### Phase 3: Integration
Add the UI indicator ("Continuing from: '...'") and "Clear context" button. Wire context clearing into file upload and table removal flows. Add unit tests for the server-side prompt modification and an E2E test for the full conversational flow.

## Step by Step Tasks

### Step 1: Add conversation context fields to server data model
- Open `app/server/core/data_models.py`
- Add two optional fields to `QueryRequest`:
  - `previous_query: Optional[str] = None` -- the previous natural language question
  - `previous_sql: Optional[str] = None` -- the SQL that was generated for that question

### Step 2: Update LLM prompt to include conversation context
- Open `app/server/core/llm_processor.py`
- Modify `generate_sql_with_openai()` and `generate_sql_with_anthropic()` to accept optional `previous_query` and `previous_sql` parameters
- When both are provided, prepend a conversation context block to the prompt before the current query:
  ```
  Previous conversation context:
  User asked: "{previous_query}"
  Generated SQL: {previous_sql}

  Now the user is asking a follow-up question. Use the previous query and SQL as context to understand references like "that", "those results", "filter that", etc.
  ```
- Update `generate_sql()` to extract `previous_query` and `previous_sql` from the `QueryRequest` and pass them to the provider-specific functions

### Step 3: Update server endpoint to pass context through
- Open `app/server/server.py`
- The `process_natural_language_query` endpoint already passes the full `request` object to `generate_sql()`, so verify that the new fields flow through correctly. No changes should be needed here since `generate_sql()` receives the full `QueryRequest`.

### Step 4: Update client TypeScript types
- Open `app/client/src/types.d.ts`
- Add optional fields to `QueryRequest` interface:
  - `previous_query?: string`
  - `previous_sql?: string`

### Step 5: Add conversation context state and logic to client
- Open `app/client/src/main.ts`
- Add module-level state variables after the existing global state comment:
  - `let previousQuery: string | null = null`
  - `let previousSql: string | null = null`
- In `executeQuery()`:
  - Include `previous_query: previousQuery ?? undefined` and `previous_sql: previousSql ?? undefined` in the `api.processQuery()` call
  - On success: store the query and response SQL (`previousQuery = query; previousSql = response.sql`)
  - On error: do NOT update `previousQuery`/`previousSql` (failed queries don't carry forward)
- Create a helper function `clearConversationContext()` that sets both to `null` and hides the context indicator UI
- Create a helper function `updateContextIndicator()` that shows/hides the "Continuing from" label based on whether `previousQuery` is set
- Call `clearConversationContext()` in `handleFileUpload()` on successful upload
- Call `clearConversationContext()` in `removeTable()` after successful table removal (uploading a new CSV that replaces a table goes through `handleFileUpload`, which covers acceptance criterion 5)

### Step 6: Add context indicator UI to HTML
- Open `app/client/index.html`
- Add a context indicator div inside `#query-section`, between the textarea and `.query-controls`:
  ```html
  <div id="context-indicator" class="context-indicator" style="display: none;">
    <span id="context-label" class="context-label"></span>
    <button id="clear-context-button" class="clear-context-button">Clear context</button>
  </div>
  ```

### Step 7: Add styles for context indicator
- Open `app/client/src/style.css`
- Add styles for `.context-indicator`, `.context-label`, and `.clear-context-button`:
  - `.context-indicator`: flex row, align-items center, gap, small padding, subtle background (e.g., light blue/gray), rounded corners, margin-top
  - `.context-label`: small font size, color muted, truncate long text with ellipsis
  - `.clear-context-button`: small text button, no border, muted color, hover underline

### Step 8: Wire up context indicator in client JS
- In `app/client/src/main.ts`:
- In `updateContextIndicator()`: if `previousQuery` is set, show the `#context-indicator` div and set `#context-label` text to `Continuing from: '${truncated query}'` (truncate to ~50 chars with ellipsis); otherwise hide it
- Call `updateContextIndicator()` after setting context in `executeQuery()` success path
- Call `updateContextIndicator()` inside `clearConversationContext()`
- Add click handler for `#clear-context-button` in `initializeQueryInput()` that calls `clearConversationContext()`

### Step 9: Add unit tests for conversation context in prompt generation
- Open `app/server/tests/core/test_llm_processor.py`
- Add tests:
  - `test_generate_sql_with_openai_with_context`: Verify that when `previous_query` and `previous_sql` are provided, the prompt includes the conversation context block
  - `test_generate_sql_with_anthropic_with_context`: Same for Anthropic path
  - `test_generate_sql_without_context`: Verify that when context fields are `None`, the prompt is unchanged (backward compatible)
  - `test_generate_sql_routes_context`: Verify `generate_sql()` passes context from `QueryRequest` to the provider function

### Step 10: Create E2E test file for conversational follow-ups
- Create `.claude/commands/e2e/test_conversational_followups.md` with the following test structure:
  - **User Story**: As a user, I want to ask follow-up questions that reference my previous query
  - **Test Steps**:
    1. Navigate to the application URL
    2. Take a screenshot of the initial state
    3. Load sample "Users Data" via the upload modal
    4. Verify no context indicator is visible
    5. Enter and submit query: "Show me all users"
    6. Verify results appear with SQL translation
    7. Take a screenshot showing results
    8. Verify context indicator appears: "Continuing from: 'Show me all users'"
    9. Take a screenshot showing the context indicator
    10. Enter and submit follow-up: "filter that by city = 'New York'"
    11. Verify results appear and SQL contains a WHERE clause referencing city
    12. Take a screenshot of follow-up results
    13. Click "Clear context" button
    14. Verify context indicator disappears
    15. Take a screenshot showing context cleared
  - **Success Criteria**: Context indicator visible after first query, follow-up produces valid SQL without re-specifying table, Clear context button removes indicator, screenshots taken at each key step

### Step 11: Run validation commands
- Run all validation commands listed below to confirm zero regressions

## Testing Strategy
### Unit Tests
- Test that `QueryRequest` accepts and correctly serializes `previous_query` and `previous_sql` fields
- Test that `generate_sql_with_openai()` includes conversation context in prompt when provided
- Test that `generate_sql_with_anthropic()` includes conversation context in prompt when provided
- Test that prompt is unchanged when context fields are `None` (backward compatibility)
- Test that `generate_sql()` correctly extracts and passes context from `QueryRequest`

### Edge Cases
- Both `previous_query` and `previous_sql` are `None` (standalone mode) -- should behave identically to current behavior
- Only one of `previous_query`/`previous_sql` is provided -- treat as no context (both must be present)
- Very long previous query text -- should not break prompt construction
- Previous SQL contains special characters or quotes -- must be safely interpolated
- Rapid successive queries -- context should update to most recent successful query
- Failed query followed by new query -- context should still reference the last *successful* query
- File upload clears context even if there was an active context
- Multiple file uploads in succession -- context stays cleared

## Acceptance Criteria
1. Run "show all users", then "filter that by city = 'New York'" -- the second query produces correct SQL without re-specifying the table
2. A "Continuing from: '{query}'" label is visible when context is active
3. Clicking "Clear context" removes the label; the next query is standalone
4. Failed queries do not carry forward as context
5. Uploading a new CSV clears existing context

## Validation Commands
Execute every command to validate the feature works correctly with zero regressions.

- Read `.claude/commands/test_e2e.md`, then read and execute `.claude/commands/e2e/test_conversational_followups.md` E2E test to validate conversational follow-up functionality works end-to-end
- `cd /Users/pzrinscak/dev/idd/tac-7/trees/db4c0b4b/app/server && source .venv/bin/activate && uv run pytest` - Run server tests to validate the feature works with zero regressions
- `cd /Users/pzrinscak/dev/idd/tac-7/trees/db4c0b4b/app/client && bun tsc --noEmit` - Run frontend type checks to validate no type errors
- `cd /Users/pzrinscak/dev/idd/tac-7/trees/db4c0b4b/app/client && bun run build` - Run frontend build to validate the feature compiles with zero regressions

## Notes
- The conversation context is intentionally client-side only (no server session state). This keeps the server stateless and avoids session management complexity.
- Context is limited to one turn of history (previous query + SQL). Multi-turn history could be a future enhancement but adds prompt length concerns.
- The prompt injection of previous SQL is safe because the SQL was generated by the LLM itself in the prior turn -- it's not arbitrary user input being executed.
- No new libraries are needed for this feature.
- The `api.processQuery()` in `client.ts` already serializes the full request object via `JSON.stringify(request)`, so adding new optional fields to `QueryRequest` will automatically include them in API calls.
