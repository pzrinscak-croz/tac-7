# Data Preview with Inline Editing

**ADW ID:** 13
**Date:** 2026-03-27
**Specification:** specs/issue-2fb164c9-adw-13-sdlc_planner-data-preview-inline-editing.md

## Overview

This feature adds a paginated data preview modal to the Natural Language SQL Interface, accessible by clicking any table name in the schema panel. Users can browse table data 50 rows at a time and perform inline CRUD operations — editing cells in place, adding new rows, and deleting existing rows — all of which persist immediately to the SQLite database.

## What Was Built

- Clickable table names in the schema panel that open a preview modal
- Paginated table preview (50 rows/page) with column headers and "Page X of Y" navigation
- Inline cell editing: click a cell to edit, Enter to save, Escape to cancel
- "Add Row" button to insert a blank row using SQLite `DEFAULT VALUES`
- "Delete Row" button per row with browser confirmation dialog
- Schema panel row count refresh after every add/delete mutation
- Four new REST API endpoints for preview, update, insert, and delete
- New `table_editor.py` core module with safe DML construction
- New Pydantic models for request/response validation
- Unit test suite for `table_editor.py` covering happy paths and error cases

## Technical Implementation

### Files Modified

- `app/server/core/table_editor.py`: New core module — `get_table_preview`, `update_table_row`, `insert_table_row`, `delete_table_row`
- `app/server/core/data_models.py`: Added `TablePreviewResponse`, `RowUpdateRequest`, `RowInsertRequest`, `RowMutationResponse`
- `app/server/server.py`: Four new route handlers delegating to `table_editor`
- `app/server/tests/test_table_editor.py`: Unit tests using a temp SQLite DB fixture
- `app/client/src/api/client.ts`: Added `getTablePreview`, `updateTableRow`, `insertTableRow`, `deleteTableRow`
- `app/client/src/types.d.ts`: Added `TablePreviewResponse` and `RowMutationResponse` TypeScript types
- `app/client/index.html`: Added `#preview-modal` HTML structure with toolbar, table container, and pagination footer
- `app/client/src/main.ts`: Preview modal logic — open/close, page loading, cell editing, add/delete row, pagination, schema refresh
- `app/client/src/style.css`: Styles for the preview modal overlay, editable cells, pagination controls, and row action buttons

### Key Changes

- **DML security model**: `table_editor.py` uses `escape_identifier()` for all table and column names and `?` parameterized placeholders for all values. It intentionally bypasses `validate_sql_query()` (designed for user-supplied SQL strings) since queries are constructed internally.
- **rowid as stable identifier**: All preview queries use `SELECT rowid, * FROM [table]`; rowid is stored as a `data-rowid` attribute on each `<tr>` and used for update/delete operations without modifying existing table schemas.
- **Empty row insert**: When "Add Row" is clicked, an empty `values` dict triggers `INSERT INTO [table] DEFAULT VALUES`, filling all columns with their SQLite defaults (typically NULL).
- **Schema panel refresh**: After any insert or delete, `loadSchema()` is called to update the row count displayed next to the table name in the schema panel.
- **Modal pattern**: The preview modal follows the existing upload modal pattern in `index.html` and `style.css` (same backdrop, close button, z-index layering) for visual consistency.

## How to Use

1. Upload a CSV, JSON, or JSONL file to create a table (or use an existing table).
2. In the schema panel on the left, click any table name — it is now rendered as a clickable button.
3. The preview modal opens showing the first 50 rows with all column headers.
4. Use **Prev / Next** buttons or observe **"Page X of Y"** to navigate through pages.
5. Click any data cell to enter edit mode — an input field appears with the current value.
   - Press **Enter** to save the change (sends a PATCH request).
   - Press **Escape** to cancel and restore the original value.
6. Click **Add Row** in the modal toolbar to insert a new blank row at the end of the table.
7. Click **Delete** on any row, then confirm the browser dialog to permanently remove that row.
8. Close the modal with the **×** button — schema panel row counts are already up to date.

## Configuration

No new configuration or environment variables are required. The feature uses the existing SQLite database at `db/database.db` (same path as `sql_processor.py`).

## Testing

```bash
# Unit tests for the table_editor module
cd app/server && uv run pytest tests/test_table_editor.py

# Full server test suite (zero regressions)
cd app/server && uv run pytest

# TypeScript type checking
cd app/client && bun tsc --noEmit

# Frontend build
cd app/client && bun run build
```

The unit tests in `test_table_editor.py` use a temporary SQLite database fixture (no mocks) and cover: paginated preview, second-page offsets, invalid table names, row update, invalid column names (SQL keywords), row insert (row count increment), row delete (row count decrement), and invalid rowid values.

## Notes

- The `rowid` column is included in the preview response but is **not rendered as an editable cell** in the UI — it is tracked via `data-rowid` on the `<tr>` element and used only as the record locator for mutations.
- Updating or deleting a rowid that no longer exists returns success with 0 rows affected (SQLite behavior); the frontend reloads the current page.
- Inserting into a table with NOT NULL constraints without providing values will return a SQLite error propagated to the client.
- `limit` values outside the range 1–200 return a 400 validation error from the preview endpoint.
- No new Python or npm dependencies were added — all functionality uses `sqlite3`, `math` (stdlib) and existing FastAPI/Pydantic/TypeScript tooling.
