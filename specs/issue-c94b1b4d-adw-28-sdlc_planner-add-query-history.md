# Feature: Query History

## Metadata
issue_number: `c94b1b4d`
adw_id: `28`
issue_json: ``

## Feature Description
Add a query history feature that stores the last 20 successful queries in localStorage and displays them in a dropdown below the query input. Users can click a history entry to re-populate the input and re-run the query, remove individual entries with an "x" button, or clear all history at once. This is a client-only feature requiring no backend changes.

## User Story
As a user of the Natural Language SQL Interface
I want to see and re-use my recent queries from a history dropdown
So that I can quickly re-run previous queries without retyping them

## Problem Statement
Users frequently run similar or identical queries but must retype them each time. There is no persistence of query activity across sessions, making it tedious to revisit past queries or recall what was previously asked.

## Solution Statement
Implement a client-side query history system using localStorage. On each successful query, save `{query, sql, timestamp}` to a capped list of 20 entries (deduped by query text, keeping the most recent timestamp). Display a dropdown below the query input showing recent queries. Clicking an entry populates the input and re-runs the query. Each entry has an "x" button for removal, and a "Clear all" button empties the list. Empty history shows "No recent queries".

## Relevant Files
Use these files to implement the feature:

- `app/client/src/main.ts` — Main application file containing `initializeQueryInput()`, `executeQuery()`, and `displayResults()`. This is where query history save logic will be triggered after successful queries and where the history dropdown will be initialized.
- `app/client/src/types.d.ts` — TypeScript type definitions. Add the `QueryHistoryEntry` interface here.
- `app/client/src/style.css` — Application styles. Add CSS for the query history dropdown, entries, remove buttons, and clear-all button. Reference existing patterns (e.g., `.query-section`, `.remove-table-button`, `.modal` patterns).
- `app/client/index.html` — HTML structure. Add the query history dropdown container element inside the `#query-section`.
- `app/client/src/api/client.ts` — API client (read-only reference to understand the query flow).
- `.claude/commands/test_e2e.md` — Read this to understand how to create an E2E test file.
- `.claude/commands/e2e/test_basic_query.md` — Read this as an example E2E test format.

### New Files
- `app/client/src/queryHistory.ts` — New module encapsulating all query history localStorage logic (save, load, remove, clear, dedupe, cap at 20).
- `.claude/commands/e2e/test_query_history.md` — E2E test file for validating query history functionality.

## Implementation Plan
### Phase 1: Foundation
Define the `QueryHistoryEntry` type and create the `queryHistory.ts` module with pure localStorage CRUD functions. This module will be testable in isolation and have no DOM dependencies.

### Phase 2: Core Implementation
Add the HTML dropdown container to `index.html`. Implement the dropdown UI rendering and interaction logic in `main.ts` (or as a new initialization function `initializeQueryHistory()`). Wire up the save-on-success hook inside `executeQuery()`. Add all necessary CSS styles.

### Phase 3: Integration
Connect history entry clicks to re-populate the input and trigger query execution. Ensure the dropdown closes on outside click and after selection. Verify all acceptance criteria including deduplication, 20-entry cap, persistence across refresh, and empty-state messaging.

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

### Task 1: Add QueryHistoryEntry type
- Open `app/client/src/types.d.ts`
- Add the `QueryHistoryEntry` interface:
  ```typescript
  interface QueryHistoryEntry {
    query: string;
    sql: string;
    timestamp: number;
  }
  ```

### Task 2: Create queryHistory.ts module
- Create `app/client/src/queryHistory.ts` with the following exported functions:
  - `getHistory(): QueryHistoryEntry[]` — Read and parse from localStorage key `queryHistory`, return empty array if missing/corrupt
  - `saveToHistory(entry: QueryHistoryEntry): void` — Add entry to history, deduplicate by `query` text (keep newest timestamp), cap at 20 entries (drop oldest), write back to localStorage
  - `removeFromHistory(query: string): void` — Remove a specific entry by query text, write back
  - `clearHistory(): void` — Remove the localStorage key entirely
- Use `localStorage.getItem('queryHistory')` / `localStorage.setItem('queryHistory', JSON.stringify(...))`
- Wrap JSON.parse in try/catch to handle corrupt data gracefully

### Task 3: Create E2E test file
- Read `.claude/commands/test_e2e.md` and `.claude/commands/e2e/test_basic_query.md` to understand the format
- Create `.claude/commands/e2e/test_query_history.md` with test steps that validate:
  1. Navigate to the app, upload sample data (users)
  2. Run a successful query (e.g., "Show me all users")
  3. Verify the query appears in the history dropdown
  4. Run a second query (e.g., "Count the users")
  5. Verify both queries appear in history (most recent first)
  6. Click the first history entry — verify input is populated and query re-runs
  7. Click the "x" on a history entry — verify it is removed
  8. Click "Clear all" — verify history is empty and shows "No recent queries"
  9. Refresh the page — verify history persists (run a query first, refresh, check dropdown)
  10. Take screenshots at key verification points

### Task 4: Add HTML structure for history dropdown
- In `app/client/index.html`, add a history dropdown container directly after the `<textarea>` element and before the `.query-controls` div, inside the `#query-section`:
  ```html
  <div id="query-history-dropdown" class="query-history-dropdown" style="display: none;">
    <div class="query-history-header">
      <span class="query-history-title">Recent Queries</span>
      <button id="clear-history-button" class="query-history-clear">Clear all</button>
    </div>
    <div id="query-history-list" class="query-history-list"></div>
  </div>
  ```

### Task 5: Add CSS styles for query history dropdown
- In `app/client/src/style.css`, add styles for:
  - `.query-history-dropdown` — Positioned below the textarea, white background, border, rounded corners, shadow, max-height with overflow-y scroll, z-index to float above content
  - `.query-history-header` — Flex row with title and "Clear all" button, border-bottom separator
  - `.query-history-title` — Small, muted heading text
  - `.query-history-clear` — Small text button styled like a link, uses `--error-color` on hover
  - `.query-history-list` — Container for history entries
  - `.query-history-item` — Flex row with query text and remove button, hover background, cursor pointer, padding
  - `.query-history-item:hover` — Light background highlight
  - `.query-history-query` — Truncated query text (ellipsis overflow), flex-grow
  - `.query-history-sql` — Small muted text showing the SQL below the query text
  - `.query-history-remove` — Small "x" button, hidden by default, shown on parent hover, styled like `.remove-table-button`
  - `.query-history-empty` — Italic muted text for "No recent queries" message
- Follow existing design patterns: use CSS variables (`--border-color`, `--text-secondary`, `--surface`, etc.), consistent border-radius (8px), transitions

### Task 6: Implement query history UI in main.ts
- Import `getHistory`, `saveToHistory`, `removeFromHistory`, `clearHistory` from `./queryHistory`
- Create `initializeQueryHistory()` function that:
  - Gets references to `#query-history-dropdown`, `#query-history-list`, `#clear-history-button`, `#query-input`
  - Implements `renderHistoryDropdown()` to populate the list:
    - Call `getHistory()`
    - If empty, show "No recent queries" message with class `query-history-empty`
    - If has entries, render each as a `.query-history-item` div containing:
      - A `.query-history-query` span with the query text (truncated via CSS)
      - A `.query-history-remove` button with "×"
    - Each item click: set `queryInput.value` to the entry's query, hide dropdown, trigger query execution
    - Each remove button click (with `stopPropagation`): call `removeFromHistory(query)`, re-render
  - Wire up `#clear-history-button` click: call `clearHistory()`, re-render
  - Show dropdown on input focus (if history exists or show empty state)
  - Hide dropdown on outside click (use `document.addEventListener('click', ...)` with target checks)
  - Hide dropdown after selecting an entry
- Call `initializeQueryHistory()` in the `DOMContentLoaded` handler alongside existing initializers
- Expose a `refreshHistory` or similar mechanism so `executeQuery` can trigger a re-render after saving

### Task 7: Wire up history save on successful query
- In `main.ts`, inside the `executeQuery()` function, after `displayResults(response, query)` succeeds and before clearing the input:
  - Call `saveToHistory({ query, sql: response.sql, timestamp: Date.now() })`
  - Trigger history dropdown re-render
- Ensure this only happens on success (not in the catch block)
- Ensure failed queries (those that throw or return an error) do NOT save to history

### Task 8: Handle query re-execution from history
- When a history item is clicked, set the textarea value and programmatically trigger query execution
- Reuse the existing `executeQuery()` function — ensure it's accessible from `initializeQueryHistory()`
- This may require restructuring `initializeQueryInput()` to expose `executeQuery` or moving it to module scope

### Task 9: Run validation commands
- Run `cd app/server && uv run pytest` to verify no backend regressions
- Run `cd app/client && bun tsc --noEmit` to verify TypeScript compiles
- Run `cd app/client && bun run build` to verify production build succeeds
- Read `.claude/commands/test_e2e.md`, then read and execute `.claude/commands/e2e/test_query_history.md` to validate the feature end-to-end

## Testing Strategy
### Unit Tests
- `queryHistory.ts` functions can be tested by mocking localStorage:
  - `getHistory()` returns empty array when localStorage is empty
  - `getHistory()` returns empty array when localStorage has corrupt JSON
  - `saveToHistory()` adds entry and persists to localStorage
  - `saveToHistory()` deduplicates by query text, keeping newest timestamp
  - `saveToHistory()` caps at 20 entries, dropping oldest
  - `removeFromHistory()` removes correct entry by query text
  - `clearHistory()` removes the localStorage key

### Edge Cases
- Corrupt/invalid JSON in localStorage — should gracefully reset to empty array
- localStorage unavailable (private browsing in some browsers) — should degrade gracefully without errors
- Very long query text — should be truncated in the dropdown via CSS ellipsis
- Rapid successive queries — each should save correctly
- Duplicate query run multiple times — only appears once with latest timestamp
- Exactly 20 entries then one more — oldest should be dropped
- Clicking history entry while a query is in progress — should be ignored (respect `isQueryInProgress`)
- Empty query input with history dropdown open — dropdown should still function
- Special characters in queries — should round-trip through JSON serialization correctly

## Acceptance Criteria
1. After a successful query, it appears at the top of the history dropdown
2. Clicking a history entry populates the input and re-runs the query
3. Individual entries can be removed with an "x" button; "Clear all" empties the list
4. History survives page refresh (persisted in localStorage)
5. Duplicate queries appear only once (most recent timestamp wins)
6. Failed queries are not added to history
7. Maximum 20 entries; oldest dropped when exceeding the limit
8. Empty history shows a message like "No recent queries", not a blank dropdown
9. TypeScript compiles with no errors (`bun tsc --noEmit`)
10. Production build succeeds (`bun run build`)
11. Server tests pass with zero regressions (`uv run pytest`)

## Validation Commands
Execute every command to validate the feature works correctly with zero regressions.

- `cd app/server && uv run pytest` - Run server tests to validate the feature works with zero regressions
- `cd app/client && bun tsc --noEmit` - Run frontend tests to validate the feature works with zero regressions
- `cd app/client && bun run build` - Run frontend build to validate the feature works with zero regressions
- Read `.claude/commands/test_e2e.md`, then read and execute `.claude/commands/e2e/test_query_history.md` E2E test file to validate this functionality works

## Notes
- This is a client-only feature — no backend changes required
- The `queryHistory.ts` module is intentionally separated from `main.ts` to keep concerns clean and allow potential reuse
- localStorage key is `queryHistory` — if we ever need to migrate the schema, we can version the key
- The dropdown should feel lightweight and unobtrusive — it's a convenience feature, not a primary interaction
- Consider adding keyboard navigation (up/down arrows) in the dropdown as a future enhancement, but it is out of scope for this issue
