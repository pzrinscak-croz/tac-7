# Feature: Conversational Follow-ups

## Metadata
issue_number: `34e4db63`
adw_id: `18`
issue_json: ``

## Feature Description
Add conversational follow-up support to the natural language SQL interface. After running a query, the next query automatically includes the previous question and generated SQL as context so the LLM can handle follow-ups like "now filter that by city" or "show that as percentages instead." A "Clear context" button resets to standalone mode. This enables a more natural, iterative data exploration workflow without requiring users to repeat themselves.

## User Story
As a data analyst
I want to ask follow-up questions that reference my previous query
So that I can iteratively refine and explore my data without re-specifying tables and conditions each time

## Problem Statement
Currently, each query is processed in isolation. Users must fully specify every query from scratch, even when they want to make small modifications to a previous result (e.g., add a filter, change sorting, show percentages). This makes iterative data exploration tedious and unnatural.

## Solution Statement
Track the last successful query and its generated SQL on the client side. Send this context with subsequent requests so the LLM can produce SQL that builds on the previous result. Display a "Continuing from: '{query}'" label when context is active, and provide a "Clear context" button to reset. Failed queries and new CSV uploads automatically clear context to prevent confusion.

## Relevant Files
Use these files to implement the feature:

**Server:**
- `app/server/core/data_models.py` — Add optional `previous_query` and `previous_sql` fields to `QueryRequest`
- `app/server/core/llm_processor.py` — Modify prompt construction to include conversation context when previous query/SQL are provided
- `app/server/server.py` — No changes needed (passes `QueryRequest` through to `generate_sql`)
- `app/server/tests/core/test_llm_processor.py` — Add tests for prompt construction with conversation context

**Client:**
- `app/client/src/main.ts` — Track last query/SQL pair in state, send with next request, show "Continuing from..." label, add "Clear context" button, clear context on upload and failure
- `app/client/src/api/client.ts` — Update `processQuery` to pass `previous_query` and `previous_sql` fields
- `app/client/src/types.d.ts` — Update `QueryRequest` type to include optional previous_query/previous_sql fields
- `app/client/src/style.css` — Add styles for the "Continuing from..." label and "Clear context" button
- `app/client/index.html` — Add container element for the context indicator UI

**E2E Testing:**
- Read `.claude/commands/test_e2e.md` and `.claude/commands/e2e/test_basic_query.md` to understand E2E test format
- `.claude/commands/e2e/test_conversational_follow_ups.md` — New E2E test file for this feature

### New Files
- `.claude/commands/e2e/test_conversational_follow_ups.md` — E2E test spec for conversational follow-ups

## Implementation Plan

### Phase 1: Foundation
Extend the server-side data model and prompt construction to accept and use conversation context. This is the foundation because the client changes depend on the server accepting these new fields.

### Phase 2: Core Implementation
Update the client to track query/SQL pairs, send context with requests, and render the "Continuing from..." indicator with a "Clear context" button. Wire up context clearing on CSV upload and failed queries.

### Phase 3: Integration
Add unit tests for the server-side prompt changes, create an E2E test, and validate all acceptance criteria end-to-end.

## Step by Step Tasks

### Step 1: Update server data models
- In `app/server/core/data_models.py`, add two optional fields to `QueryRequest`:
  - `previous_query: Optional[str] = None` — The previous natural language query
  - `previous_sql: Optional[str] = None` — The SQL generated from the previous query
- Both fields should use `Field(default=None, description="...")` for documentation

### Step 2: Update LLM prompt construction
- In `app/server/core/llm_processor.py`, modify both `generate_sql_openai()` and `generate_sql_anthropic()` to accept and use conversation context
- When `previous_query` and `previous_sql` are provided in the request, append a conversation context section to the prompt before the current query, e.g.:
  ```
  Previous conversation context:
  User asked: "{previous_query}"
  Generated SQL: {previous_sql}

  Now the user is asking a follow-up question. Use the previous context to understand references like "that", "those results", "filter it", etc.
  ```
- When no previous context is provided, the prompt remains unchanged (backward compatible)
- Update the `generate_sql()` routing function to pass the full request (it already does)

### Step 3: Add server unit tests
- In `app/server/tests/core/test_llm_processor.py`, add tests:
  - Test that OpenAI prompt includes conversation context when `previous_query` and `previous_sql` are provided
  - Test that Anthropic prompt includes conversation context when `previous_query` and `previous_sql` are provided
  - Test that prompt is unchanged when no previous context is provided (backward compatibility)
  - Test that partial context (only `previous_query` without `previous_sql` or vice versa) is handled gracefully — only include context when both are present
- Run `cd app/server && uv run pytest` to validate

### Step 4: Update client TypeScript types
- In `app/client/src/types.d.ts`, update the `QueryRequest` interface (or add it if not present) to include:
  - `previous_query?: string`
  - `previous_sql?: string`

### Step 5: Update client API layer
- In `app/client/src/api/client.ts`, update the `processQuery` method to pass through `previous_query` and `previous_sql` from the request object to the API call

### Step 6: Add context tracking and UI to client
- In `app/client/src/main.ts`:
  - Add module-level state variables: `let lastQuery: string | null = null` and `let lastSql: string | null = null`
  - After a successful query response (no error), store the query text and generated SQL in these variables
  - On failed query (error response), do NOT update the context variables (acceptance criteria #4)
  - When submitting a query, include `previous_query: lastQuery` and `previous_sql: lastSql` in the request if they are set
- In `app/client/index.html`, add a context indicator container between the query input area and results, e.g.:
  ```html
  <div id="context-indicator" style="display: none;">
    <span id="context-label"></span>
    <button id="clear-context-button">Clear context</button>
  </div>
  ```
- In `app/client/src/main.ts`:
  - After storing context, show the indicator: set `context-label` text to `Continuing from: '{truncated query}'` and display the container
  - Wire the "Clear context" button to set `lastQuery = null`, `lastSql = null`, and hide the indicator
  - Truncate the displayed query to ~50 characters with ellipsis if longer

### Step 7: Clear context on CSV upload
- In `app/client/src/main.ts`, in the `handleFileUpload()` success path and `loadSampleData()` success path:
  - Set `lastQuery = null` and `lastSql = null`
  - Hide the context indicator
- This satisfies acceptance criteria #5

### Step 8: Add styles for context indicator
- In `app/client/src/style.css`, add styles for:
  - `#context-indicator` — A subtle bar/label (e.g., light background, small font, flex layout with space-between)
  - `#context-label` — Italic or muted text style showing the previous query
  - `#clear-context-button` — Small, understated button (text-style or link-style) to clear context

### Step 9: Create E2E test file
- Create `.claude/commands/e2e/test_conversational_follow_ups.md` following the format in `test_basic_query.md` and `test_complex_query.md`
- The E2E test should validate:
  1. Upload sample users data
  2. Run "show all users" query — verify results appear
  3. Verify "Continuing from: 'show all users'" label appears
  4. Run follow-up "filter that by city = 'New York'" — verify correct SQL is generated without re-specifying the table
  5. Click "Clear context" — verify label disappears
  6. Run a standalone query — verify it works without context
  7. Take screenshots at key steps

### Step 10: Run validation commands
- Execute all validation commands listed below to confirm zero regressions

## Testing Strategy

### Unit Tests
- Server: Test prompt construction with and without conversation context for both OpenAI and Anthropic providers
- Server: Test that partial context (only one of previous_query/previous_sql) does not inject incomplete context
- Server: Test backward compatibility — requests without context fields work identically to before

### Edge Cases
- Very long previous queries — ensure prompt doesn't exceed token limits (truncate if necessary)
- Previous SQL that contains special characters or quotes — ensure proper escaping in prompt
- Rapid sequential queries — debounce already handles this, but ensure context updates correctly
- Failed queries should not update context (acceptance criteria #4)
- Uploading a new CSV clears context (acceptance criteria #5)
- Context indicator shows truncated query text for very long queries
- Partial context fields (only `previous_query` without `previous_sql`) — should be treated as no context

## Acceptance Criteria
1. Run "show all users", then "filter that by city = 'New York'" — the second query produces correct SQL without re-specifying the table
2. A "Continuing from: '{query}'" label is visible when context is active
3. Clicking "Clear context" removes the label; the next query is standalone
4. Failed queries do not carry forward as context
5. Uploading a new CSV clears existing context
6. All existing server tests pass with zero regressions
7. All new unit tests pass
8. Frontend builds without TypeScript errors
9. E2E test validates the conversational follow-up flow

## Validation Commands
Execute every command to validate the feature works correctly with zero regressions.

- `cd app/server && uv run pytest` - Run server tests to validate the feature works with zero regressions
- `cd app/client && bun tsc --noEmit` - Run frontend tests to validate the feature works with zero regressions
- `cd app/client && bun run build` - Run frontend build to validate the feature works with zero regressions
- Read `.claude/commands/test_e2e.md`, then read and execute `.claude/commands/e2e/test_conversational_follow_ups.md` E2E test to validate this functionality works

## Notes
- No new libraries are needed for this feature — it uses existing Pydantic models, fetch API, and DOM manipulation
- The conversation context is limited to one previous query/SQL pair (not a full chat history). This keeps the implementation simple while covering the most common follow-up patterns
- The prompt engineering for conversation context should be carefully worded to help the LLM understand that references like "that", "those", "it" refer to the previous query results
- Future enhancement: could extend to multi-turn context (array of previous queries) but single-turn is sufficient for the stated requirements
