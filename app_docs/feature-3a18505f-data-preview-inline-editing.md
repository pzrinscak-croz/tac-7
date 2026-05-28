# Data Preview with Inline Editing

**ADW ID:** 3a18505f
**Date:** 2026-05-28
**Specification:** specs/issue-3a18505f-adw-42-sdlc_planner-data-preview-inline-editing.md

## Overview

Adds a paginated data preview modal that opens when a user clicks a table name in the schema panel. Cells are click-to-edit (Enter to save, Escape to revert), and users can add or delete rows with dedicated controls. All changes persist immediately to SQLite, and the schema panel row counts re-sync after every mutation.

## What Was Built

- Four new server endpoints for table CRUD scoped to a single table (preview with pagination, update cell, insert row, delete row by rowid)
- A `users`/`rowid`-based mutation model that works for every uploaded file table without requiring an explicit primary key
- Preview modal in the client with a paginated grid (50 rows per page), `Page X of Y` indicator, and Prev/Next buttons
- Click-to-edit cells using `contenteditable`, with Enter to commit and Escape to revert
- "Add Row" toolbar button that inserts a default row and jumps the UI to the page containing it
- Per-row delete button with confirmation dialog
- Pydantic models and matching TypeScript types for the new request/response shapes
- A 12-case server test suite covering pagination math, identifier-injection rejection, 404s, and round-trip persistence
- A Playwright E2E test exercising the full edit / add / delete / persistence flow

## Technical Implementation

### Files Modified

- `app/server/core/data_models.py`: Added `TablePreviewResponse`, `RowUpdateRequest`, `RowInsertRequest`, and `RowMutationResponse` Pydantic models
- `app/server/server.py`: Added `GET /api/table/{name}/preview`, `PATCH /api/table/{name}/row`, `POST /api/table/{name}/row`, and `DELETE /api/table/{name}/row/{rowid}` endpoints plus shared `_get_table_columns` and `_get_row_count` helpers
- `app/server/tests/test_table_crud.py`: New 12-case pytest module exercising the four endpoints
- `app/client/src/types.d.ts`: Added TypeScript interfaces mirroring the new Pydantic models
- `app/client/src/api/client.ts`: Added `getTablePreview`, `updateTableRow`, `insertTableRow`, and `deleteTableRow` API methods
- `app/client/index.html`: Added hidden `#preview-modal` with toolbar, table container, and pagination slots
- `app/client/src/style.css`: Added styles for the preview modal, editable cells, pagination controls, add-row button, per-row delete button, and the `.table-name.clickable` affordance
- `app/client/src/main.ts`: Made schema-panel table names clickable, wired modal open/close, paginated grid rendering, cell editing, add/delete row handlers, and schema-panel refresh after each mutation
- `.claude/commands/e2e/test_data_preview_inline_editing.md`: New Playwright E2E test covering all seven acceptance criteria

### Key Changes

- New endpoints validate identifiers through `core/sql_security.validate_identifier` and use `execute_query_safely` with `{identifier}` substitution plus parameterized values. The write paths deliberately bypass `validate_sql_query` (which would reject `UPDATE`/`DELETE FROM`/raw `INSERT`) because they build fixed SQL templates from already-validated identifiers and parameterized values
- Mutations use SQLite's implicit `rowid` as the stable identifier, so the feature works for every table created via `convert_csv_to_sqlite` / `convert_json_to_sqlite` without requiring schema changes
- The preview endpoint clamps `page >= 1` and `1 <= limit <= 200`, computes `total_pages = max(1, ceil(total_rows / limit))`, and returns `rowid` alongside each row's columns so the client can target updates and deletes
- The client tracks `currentPreviewTable` and `currentPreviewPage` as module-level state; after a successful insert the UI jumps to the last page so the new row is visible, and after a delete that empties a non-first page the UI steps back one page
- Every successful mutation re-calls `loadDatabaseSchema()` so the schema panel's row count for that table stays in sync
- Insert with values builds the column list dynamically (since `execute_query_safely` only handles a fixed set of named identifier placeholders) — each column name is independently validated and escaped via `escape_identifier` before the statement is composed, then values are bound as parameters

## How to Use

### Open the preview

1. Upload a CSV/JSON file or click a "Sample Data" button so a table appears in the schema panel.
2. Click the table name (now rendered as a dotted-underline link) to open the preview modal.

### Edit a cell

1. Click any cell in the grid; it becomes editable.
2. Type a new value.
3. Press **Enter** to save (persists to SQLite immediately), or press **Escape** to revert without saving.

### Add a row

1. Click **Add Row** in the modal toolbar. A new row with default values is inserted; the UI jumps to the page containing it.
2. The schema panel row count for the table updates.

### Delete a row

1. Click the **×** button on the row you want to remove.
2. Confirm the dialog. The row is removed permanently and the schema panel row count updates.

### Paginate

- Use **Prev** / **Next** under the grid; `Page X of Y` reflects current position. Prev is disabled on page 1, Next on the last page.

## Configuration

No new configuration is required. The feature reuses:

- The existing `db/database.db` SQLite connection pattern
- `core/sql_security.py` (`validate_identifier`, `check_table_exists`, `execute_query_safely`, `escape_identifier`)
- The existing `.modal` / `.modal-content` / `.modal-header` / `.modal-body` CSS classes

The preview endpoint accepts `page` and `limit` query params (`1 <= limit <= 200`); the client always sends `limit=50`.

## Testing

### Server unit tests

```bash
cd app/server && uv run pytest tests/test_table_crud.py
```

Covers: first-page pagination, pagination math and `total_pages`, identifier rejection, missing-table 404s, update persistence, update 404 on missing rowid, update rejection of unknown columns, empty-insert null row, insert with values, delete with new count, delete 404 on missing rowid, and identifier-injection rejection across all four endpoints.

### Client type-check and build

```bash
cd app/client && bun tsc --noEmit
cd app/client && bun run build
```

### End-to-end

Read `.claude/commands/test_e2e.md`, then execute `.claude/commands/e2e/test_data_preview_inline_editing.md` — opens the modal, paginates, edits a cell, adds a row, deletes a row, reloads, and verifies the edit persisted.

## Notes

- **`rowid` as identifier.** Uploaded tables built via pandas `to_sql` do not declare a primary key. SQLite's implicit `rowid` is always present on non-`WITHOUT ROWID` tables and is the safest stable identifier for in-place edits.
- **Why bypass `validate_sql_query` on the write endpoints.** `validate_sql_query` is an aggressive denylist for LLM-generated free-form queries and would reject `UPDATE … SET`, `DELETE FROM`, and `INSERT`. The new endpoints construct fixed templates with validated identifiers and parameterized values, so identifier validation plus `allow_ddl=False` is sufficient.
- **NULL vs empty string.** v1 stores the literal cell value, including `''`. There is no explicit way to enter NULL from the UI yet.
- **Type coercion.** Edits are sent as strings; SQLite coerces for INTEGER/REAL columns. Coercion failures surface in the response `error` field rather than as a 500.
- **Concurrency.** No optimistic locking — last-write-wins. Acceptable for the single-user local-dev positioning.
- **Existing table-row `×` (remove table) button** remains independent of the new click-to-preview handler; clicking it still deletes the entire table without opening the preview.
