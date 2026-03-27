# Feature: Query History

## Metadata
issue_number: `90f63f51`
adw_id: `14`
issue_json: `{"number":14,"title":"Query History","body":"/feature\n\nadw_sdlc_iso\n\nmodel_set heavy\n\nStore the last 20 queries in localStorage. Show a small dropdown on the query input that lists recent queries. Click one to re-populate the input and re-run it.\n\n**Scope:**\n- Client-only -- save `{query, sql, timestamp}` to localStorage on each successful query\n- Dropdown list under the input, click to load, small \"x\" to clear history\n\n**Acceptance criteria:**\n1. After a successful query, it appears at the top of the history dropdown\n2. Clicking a history entry populates the input and re-runs the query\n3. Individual entries can be removed with an \"x\" button; \"Clear all\" empties the list\n4. History survives page refresh\n5. Duplicate queries appear only once (most recent timestamp)\n6. Failed queries are not added to history\n7. Maximum 20 entries; oldest dropped when exceeding the limit\n8. Empty history shows a message like \"No recent queries\", not a blank dropdown"}`

## Feature Description
Query History adds a persistent, localStorage-backed record of the last 20 successfully executed queries. A dropdown panel appears below the query input when the user clicks a "History" toggle button, listing recent queries with their timestamps. Clicking a history entry repopulates the textarea and immediately re-runs the query. Each entry has an "×" button for individual removal, and a "Clear all" link resets the entire list. Duplicate query strings are collapsed to a single entry (updated to the most recent timestamp). Failed queries are never recorded.

## User Story
As a data analyst
I want to see a list of my recent successful queries
So that I can quickly re-run or iterate on previous queries without retyping them

## Problem Statement
Users frequently run the same or similar queries across sessions. Without history, every session requires retyping queries from scratch, which wastes time and breaks analytical flow. There is currently no mechanism to recall, browse, or re-run past queries.

## Solution Statement
Implement a client-only query history stored in `localStorage` under the key `query_history`. Each successful query is saved as `{query, sql, timestamp}`. A dropdown panel rendered beneath the query input lists these entries in reverse-chronological order. Users can click an entry to repopulate the input and trigger execution, remove individual entries with "×", or wipe the list with "Clear all". The list is capped at 20 items and deduplicates on the `query` string, keeping only the most recent timestamp.

## Relevant Files

- **`app/client/src/main.ts`** — Core application logic; contains `initializeQueryInput()` where the query is submitted and `displayResults()` which is called on success. The history save hook and dropdown initialization live here.
- **`app/client/index.html`** — HTML structure for the query section. A history dropdown container will be inserted after `#query-input` within `#query-section`.
- **`app/client/src/style.css`** — All styling. New CSS rules for the history toggle button, dropdown panel, individual entries, and empty state will be appended here using existing CSS variables (`--primary-color`, `--border-color`, `--surface`, etc.).
- **`app/client/src/types.d.ts`** — TypeScript interface definitions. A new `QueryHistoryEntry` interface will be added here.

### New Files

- **`.claude/commands/e2e/test_query_history.md`** — E2E test file validating query history functionality (dropdown visibility, entry addition after query, click-to-rerun, remove entry, clear all, empty state, persistence across refresh). Read `.claude/commands/test_e2e.md` and `.claude/commands/e2e/test_basic_query.md` to understand the expected format before creating this file.

## Implementation Plan

### Phase 1: Foundation
Add the `QueryHistoryEntry` TypeScript interface and implement pure localStorage helper functions (`loadHistory`, `saveHistory`, `addToHistory`, `removeFromHistory`, `clearHistory`) in `main.ts`. These functions handle deduplication, the 20-entry cap, and serialization. No UI changes yet.

### Phase 2: Core Implementation
1. Add the HTML structure: a "History" toggle button in `.query-controls-left` and a hidden `#history-dropdown` panel below the textarea.
2. Add CSS for the dropdown panel, individual history entries, the "×" remove button, the "Clear all" link, and the empty-state message.
3. Implement `initializeQueryHistory()` in `main.ts` which:
   - Renders the current history list into the dropdown
   - Wires the toggle button to show/hide the panel
   - Wires entry click → populate textarea → execute query
   - Wires "×" buttons → remove entry → re-render
   - Wires "Clear all" → clear history → re-render

### Phase 3: Integration
Hook `addToHistory(query, sql)` into the existing success path inside `initializeQueryInput()` — immediately after `displayResults()` is called — so every successful query is automatically persisted and the dropdown is refreshed. Failed queries (caught in the `catch` block or when `response.error` is set) must not call `addToHistory`.

## Step by Step Tasks

### Step 1: Add `QueryHistoryEntry` interface to `types.d.ts`
- Open `app/client/src/types.d.ts`
- Add:
  ```typescript
  interface QueryHistoryEntry {
    query: string;
    sql: string;
    timestamp: number; // Unix ms
  }
  ```

### Step 2: Implement localStorage helper functions in `main.ts`
- Add the following functions near the top of `main.ts` (before `DOMContentLoaded`):
  - `loadHistory(): QueryHistoryEntry[]` — reads and JSON-parses `localStorage.getItem('query_history')`, returns `[]` on error
  - `saveHistory(entries: QueryHistoryEntry[]): void` — JSON-stringifies and writes to `localStorage.setItem('query_history', ...)`
  - `addToHistory(query: string, sql: string): void`:
    - Trims `query`; no-op if empty
    - Loads current history
    - Removes any existing entry with the same `query` string (case-sensitive)
    - Prepends `{ query, sql, timestamp: Date.now() }`
    - Slices to first 20 entries
    - Saves back to localStorage
  - `removeFromHistory(query: string): void` — filters out the entry matching `query`, saves
  - `clearHistory(): void` — saves `[]`

### Step 3: Add HTML structure for history toggle and dropdown
- In `app/client/index.html`, inside `.query-controls-left` div, add a "History" toggle button after the existing "Query" button:
  ```html
  <button id="history-toggle-button" class="secondary-button">History</button>
  ```
- Directly after the `</textarea>` and before `.query-controls`, add the dropdown panel:
  ```html
  <div id="history-dropdown" class="history-dropdown hidden">
    <div class="history-header">
      <span class="history-title">Recent Queries</span>
      <button id="history-clear-all" class="history-clear-all">Clear all</button>
    </div>
    <ul id="history-list" class="history-list"></ul>
  </div>
  ```

### Step 4: Create E2E test file
- Read `.claude/commands/test_e2e.md` and `.claude/commands/e2e/test_basic_query.md` to understand format
- Create `.claude/commands/e2e/test_query_history.md` with:
  - User story matching the feature
  - Test steps:
    1. Navigate to application URL
    2. Take initial screenshot
    3. Verify history toggle button is present
    4. Click history toggle button → verify dropdown opens showing "No recent queries"
    5. Take screenshot of empty history state
    6. Close dropdown
    7. Enter query "Show me all users from the users table" and submit
    8. Wait for results
    9. Click history toggle button → verify the query appears in the list
    10. Take screenshot of history with one entry
    11. Click "×" on the entry → verify it is removed → verify "No recent queries" shown
    12. Take screenshot after removal
    13. Submit the same query again
    14. Refresh the page
    15. Click history toggle → verify the entry survived the refresh
    16. Take screenshot of persisted history
    17. Click the history entry → verify input is repopulated and query re-runs
    18. Take screenshot of re-run result
    19. Click "Clear all" → verify list is empty
    20. Take final screenshot
  - Success criteria matching all 8 acceptance criteria

### Step 5: Add CSS for history UI in `style.css`
- Append new rules to `app/client/src/style.css` using existing CSS variables:
  ```css
  /* Query History */
  .history-dropdown {
    position: relative;
    background: var(--surface);
    border: 2px solid var(--border-color);
    border-radius: 8px;
    margin-top: 4px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    z-index: 100;
    overflow: hidden;
  }
  .history-dropdown.hidden { display: none; }
  .history-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 12px;
    border-bottom: 1px solid var(--border-color);
    background: #f8f9ff;
  }
  .history-title {
    font-size: 0.8rem;
    font-weight: 600;
    color: #666;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }
  .history-clear-all {
    background: none;
    border: none;
    color: var(--primary-color);
    font-size: 0.8rem;
    cursor: pointer;
    padding: 2px 6px;
    border-radius: 4px;
  }
  .history-clear-all:hover { text-decoration: underline; }
  .history-list {
    list-style: none;
    margin: 0;
    padding: 0;
    max-height: 240px;
    overflow-y: auto;
  }
  .history-empty {
    padding: 16px 12px;
    text-align: center;
    color: #999;
    font-size: 0.9rem;
    font-style: italic;
  }
  .history-item {
    display: flex;
    align-items: center;
    padding: 8px 12px;
    border-bottom: 1px solid #f0f0f0;
    cursor: pointer;
    transition: background 0.15s ease;
  }
  .history-item:last-child { border-bottom: none; }
  .history-item:hover { background: #f5f5ff; }
  .history-item-text {
    flex: 1;
    font-size: 0.9rem;
    color: #333;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-right: 8px;
  }
  .history-item-time {
    font-size: 0.75rem;
    color: #999;
    white-space: nowrap;
    margin-right: 8px;
  }
  .history-item-remove {
    background: none;
    border: none;
    color: #bbb;
    font-size: 1rem;
    line-height: 1;
    cursor: pointer;
    padding: 2px 4px;
    border-radius: 4px;
    flex-shrink: 0;
  }
  .history-item-remove:hover { color: var(--error-color); background: #fff0f0; }
  ```

### Step 6: Implement `initializeQueryHistory()` in `main.ts`
- Add the function after the helper functions (before `DOMContentLoaded`):
  ```typescript
  function renderHistoryList(listEl: HTMLUListElement, toggleButton: HTMLButtonElement): void {
    const entries = loadHistory();
    listEl.innerHTML = '';
    if (entries.length === 0) {
      const empty = document.createElement('li');
      empty.className = 'history-empty';
      empty.textContent = 'No recent queries';
      listEl.appendChild(empty);
      return;
    }
    entries.forEach((entry) => {
      const li = document.createElement('li');
      li.className = 'history-item';

      const text = document.createElement('span');
      text.className = 'history-item-text';
      text.textContent = entry.query;
      text.title = entry.query;

      const time = document.createElement('span');
      time.className = 'history-item-time';
      time.textContent = new Date(entry.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

      const remove = document.createElement('button');
      remove.className = 'history-item-remove';
      remove.textContent = '×';
      remove.title = 'Remove';
      remove.addEventListener('click', (e) => {
        e.stopPropagation();
        removeFromHistory(entry.query);
        renderHistoryList(listEl, toggleButton);
      });

      li.appendChild(text);
      li.appendChild(time);
      li.appendChild(remove);
      li.addEventListener('click', () => {
        const input = document.getElementById('query-input') as HTMLTextAreaElement;
        input.value = entry.query;
        dropdown.classList.add('hidden');
        // Trigger query execution
        document.getElementById('query-button')?.click();
      });

      listEl.appendChild(li);
    });
  }

  function initializeQueryHistory(): void {
    const toggleButton = document.getElementById('history-toggle-button') as HTMLButtonElement;
    const dropdown = document.getElementById('history-dropdown') as HTMLDivElement;
    const listEl = document.getElementById('history-list') as HTMLUListElement;
    const clearAll = document.getElementById('history-clear-all') as HTMLButtonElement;

    if (!toggleButton || !dropdown || !listEl || !clearAll) return;

    toggleButton.addEventListener('click', () => {
      const isHidden = dropdown.classList.toggle('hidden');
      if (!isHidden) {
        renderHistoryList(listEl, toggleButton);
      }
    });

    clearAll.addEventListener('click', () => {
      clearHistory();
      renderHistoryList(listEl, toggleButton);
    });
  }
  ```
- Call `initializeQueryHistory()` inside `DOMContentLoaded` alongside other `initialize*` calls.

### Step 7: Hook `addToHistory()` into the query success path in `main.ts`
- In `initializeQueryInput()`, find the block where `displayResults(response, query)` is called on success.
- Immediately after `displayResults(response, query)`, add:
  ```typescript
  addToHistory(query, response.sql);
  // Refresh dropdown if it is currently open
  const listEl = document.getElementById('history-list') as HTMLUListElement;
  const dropdown = document.getElementById('history-dropdown') as HTMLDivElement;
  const toggleButton = document.getElementById('history-toggle-button') as HTMLButtonElement;
  if (listEl && dropdown && !dropdown.classList.contains('hidden')) {
    renderHistoryList(listEl, toggleButton);
  }
  ```
- Confirm the `catch` block and error-response path do **not** call `addToHistory`.

### Step 8: Run validation commands
- Run all validation commands listed below to confirm zero regressions before committing.

## Testing Strategy

### Unit Tests
- No server-side unit tests required (client-only feature).
- The TypeScript compiler (`bun tsc --noEmit`) validates types including the new `QueryHistoryEntry` interface.

### Edge Cases
- **Empty query string** — `addToHistory` trims and skips blank input.
- **Duplicate queries** — second submission of identical query string removes old entry and prepends new one.
- **21st entry** — 21st entry causes the oldest (index 20) to be dropped.
- **localStorage unavailable** — `loadHistory` returns `[]` on JSON parse error; `saveHistory` wrapped in try/catch to silently fail.
- **Failed query** — response with `error` field set must not call `addToHistory`; verify in the catch branch too.
- **Single-entry history** — "×" removal leaves empty state message, not a blank list.
- **"Clear all" on empty list** — no-op, empty state message still shown.
- **History timestamp display** — timestamp should be human-readable (local time HH:MM).

## Acceptance Criteria
1. After a successful query, the query string appears at the top of the history dropdown with the current timestamp.
2. Clicking a history entry populates `#query-input` with the query text and immediately executes the query (equivalent to pressing the Query button).
3. Each history entry has a "×" button that removes only that entry; a "Clear all" button removes all entries.
4. History entries survive a full page refresh (persisted in `localStorage`).
5. Submitting the same query twice results in only one entry (updated to the most recent timestamp), not two.
6. Queries that return an error response (or throw a network error) are not added to history.
7. After 20 entries, the 21st entry causes the oldest entry to be dropped so the list stays at exactly 20.
8. When no history entries exist, the dropdown shows "No recent queries" instead of a blank panel.

## Validation Commands
Execute every command to validate the feature works correctly with zero regressions.

1. Read `.claude/commands/test_e2e.md`, then read and execute `.claude/commands/e2e/test_query_history.md` to validate query history functionality end-to-end.
2. `cd app/server && uv run pytest` — Run server tests to validate the feature works with zero regressions.
3. `cd app/client && bun tsc --noEmit` — Run TypeScript type checking to validate the feature works with zero regressions.
4. `cd app/client && bun run build` — Run frontend build to validate the feature works with zero regressions.

## Notes
- This is a **client-only** feature. No server changes are required.
- `localStorage` key: `query_history` (string, JSON array of `QueryHistoryEntry`).
- The dropdown is not a floating/absolute overlay — it is in-flow below the textarea within `#query-section`, keeping layout predictable and avoiding z-index conflicts.
- The "History" toggle button uses the existing `.secondary-button` class for visual consistency with "Upload".
- `renderHistoryList` is called both on toggle-open and after every mutation (add, remove, clear) to keep the UI in sync without a reactive framework.
- If `localStorage` is unavailable (e.g., private browsing with restrictions), the feature degrades gracefully: history simply isn't persisted but the UI renders with an empty list.
- No new npm/bun packages are required.
