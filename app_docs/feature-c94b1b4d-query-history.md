# Query History

**ADW ID:** 28
**Date:** 2026-03-27
**Specification:** specs/issue-c94b1b4d-adw-28-sdlc_planner-add-query-history.md

## Overview

A client-side query history feature that stores the last 20 successful queries in localStorage and displays them in a dropdown below the query input. Users can re-run previous queries with a single click, remove individual entries, or clear all history at once.

## What Was Built

- localStorage-backed query history storage with a 20-entry cap
- Dropdown UI showing recent queries below the query input textarea
- One-click query re-execution from history entries
- Individual entry removal via "×" button and bulk "Clear all" action
- Deduplication by query text (most recent timestamp wins)
- Graceful degradation when localStorage is unavailable
- Empty state messaging ("No recent queries")

## Technical Implementation

### Files Modified

- `app/client/src/types.d.ts`: Added `QueryHistoryEntry` interface (`query`, `sql`, `timestamp`)
- `app/client/src/queryHistory.ts`: New module with `getHistory()`, `saveToHistory()`, `removeFromHistory()`, and `clearHistory()` functions
- `app/client/src/main.ts`: Added `initializeQueryHistory()` function, wired save-on-success into `executeQuery()`, exposed `triggerQuery` for history clicks
- `app/client/index.html`: Added `#query-history-dropdown` container with header, clear button, and list inside `#query-section`
- `app/client/src/style.css`: Added styles for dropdown, header, items, remove buttons, hover states, and empty state

### Key Changes

- `queryHistory.ts` is a standalone module with no DOM dependencies — all localStorage CRUD is isolated and wrapped in try/catch for resilience
- `isQueryInProgress` and `triggerQuery` were lifted to module scope in `main.ts` so the history dropdown can check execution state and trigger queries
- History entries are deduped by query text on save: existing matches are removed before the new entry is prepended
- The dropdown appears on textarea focus and hides on outside click
- Remove buttons are hidden by default and revealed on hover via CSS opacity transition

## How to Use

1. Type a natural language query in the input and execute it
2. On success, the query is automatically saved to history
3. Click the query input to see the history dropdown
4. Click any history entry to re-populate the input and re-run the query
5. Hover over an entry and click "×" to remove it
6. Click "Clear all" in the dropdown header to remove all history entries
7. History persists across page refreshes via localStorage

## Configuration

- **localStorage key:** `queryHistory`
- **Maximum entries:** 20 (configurable via `MAX_ENTRIES` constant in `queryHistory.ts`)
- No backend configuration required — this is entirely client-side

## Testing

- Verify TypeScript compiles: `cd app/client && bun tsc --noEmit`
- Verify production build: `cd app/client && bun run build`
- Verify no backend regressions: `cd app/server && uv run pytest`
- E2E test: `.claude/commands/e2e/test_query_history.md`

## Notes

- This is a client-only feature with no backend changes
- Corrupt localStorage data is handled gracefully (resets to empty array)
- Very long query text is truncated via CSS text-overflow ellipsis
- Keyboard navigation (arrow keys) in the dropdown is out of scope for this iteration
