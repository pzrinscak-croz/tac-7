# Data Preview with Inline Editing

**ADW ID:** d9a18411
**Date:** 2026-05-28
**Specification:** specs/issue-45-adw-d9a18411-sdlc_planner-data-preview-inline-editing.md

## Overview

Adds a paginated, in-browser table editor for any uploaded SQLite table. Clicking a table name in the Available Tables panel opens a preview modal that shows 50 rows per page with editable cells, an "Add Row" button, and per-row "Delete" buttons. All mutations write back to SQLite through new server endpoints that reuse the existing `sql_security` injection guards.

## What Was Built

- Four new server endpoints under `/api/table/{name}/...` for preview, update, insert, and delete
- A new `core/table_crud.py` module that wraps row-level SQLite operations on top of `sql_security`
- Pydantic request/response models for the new endpoints
- A new Preview Modal in the client with editable cells, pagination, and Add/Delete row controls
- Clickable table names in the schema panel that open the preview modal
- Automatic schema panel row count refresh after insert/delete
- Unit tests for the new CRUD module covering pagination math, identifier validation, NULL handling, and rowid edge cases
- An E2E test that drives the full UI flow including persistence after refresh

## Technical Implementation

### Files Modified

- `app/server/core/data_models.py`: Added `TablePreviewRow`, `TablePreviewResponse`, `UpdateRowRequest`, `InsertRowRequest`, `RowMutationResponse` Pydantic models
- `app/server/core/table_crud.py`: New module — `get_table_preview`, `update_row_cell`, `insert_row`, `delete_row`, plus `TableCRUDError`
- `app/server/server.py`: Added `GET /api/table/{table_name}/preview`, `PATCH /api/table/{table_name}/row`, `POST /api/table/{table_name}/row`, `DELETE /api/table/{table_name}/row/{rowid}` route handlers
- `app/server/tests/test_table_crud.py`: New unit tests for the CRUD module (pagination, identifier rejection, rowid behavior, column validation, NULL handling)
- `app/client/index.html`: Added `#preview-modal` markup with toolbar, table container, and pagination controls
- `app/client/src/types.d.ts`: Added matching TS interfaces for the new payloads
- `app/client/src/api/client.ts`: Added `getTablePreview`, `updateRowCell`, `insertRow`, `deleteRow` client methods
- `app/client/src/main.ts`: Added `initializePreviewModal`, `openPreview`, `loadPreviewPage`, `renderPreviewTable`, `beginCellEdit`, `handleDeleteRow`; made schema-panel table names clickable
- `app/client/src/style.css`: Added preview modal, editable cell, pagination, and clickable-table-name styles
- `.claude/commands/e2e/test_data_preview_inline_editing.md`: New E2E test covering the full preview/edit flow

### Key Changes

- Row identity uses SQLite's implicit `rowid`. Uploaded CSV/JSON tables have no guaranteed primary key, so `rowid` is the most reliable handle and is exposed only on `<tr data-rowid>` and in API payloads — never rendered as a cell.
- All four endpoints route through `sql_security.execute_query_safely` with `identifier_params`, so table and column names are validated and escaped while values are bound as parameters. The UPDATE statement passes both `{table}` and `{column}` identifiers in a single call.
- The CRUD module accepts a `db_path` argument (default `"db/database.db"`) so tests can point at a temp SQLite file without monkeypatching.
- Server clamps `page >= 1` and `1 <= limit <= 200`. Client re-clamps after each fetch (`page = min(page, total_pages)`) so deleting the last row on the final page recovers gracefully and re-fetches the now-valid page.
- Cell edit lifecycle: click swaps the `<td>` for an `<input>`; Enter commits via PATCH; Escape and blur both revert (predictable contract — blur never silently saves).
- After successful insert or delete, the client calls `loadDatabaseSchema()` so the row-count chip in Available Tables updates without a manual refresh. PATCH does not trigger a schema reload (row count is unchanged).
- Empty `InsertRowRequest.values` results in `INSERT INTO {table} DEFAULT VALUES`; otherwise every key is validated against `PRAGMA table_info` before the parameterized INSERT runs.

## How to Use

1. Upload a CSV or JSON file (or load a sample dataset) so a table appears under "Available Tables".
2. Click the table name. The Preview modal opens showing column headers, the first 50 rows, and a "X rows total" status.
3. Click any cell to edit it. Press **Enter** to save, **Escape** (or click outside) to revert.
4. Click **+ Add Row** to insert an empty row. The modal jumps to the last page so the new row is visible, and the Available Tables row-count chip updates immediately.
5. Click **Delete** on any row, confirm the dialog, and the row is permanently removed. The row count updates.
6. Use **Prev** / **Next** to paginate when the table has more than 50 rows. The label reads `Page X of Y`.
7. Close the modal with the × button or by clicking the backdrop.

## Configuration

No additional configuration is required. The feature uses:
- The existing `db/database.db` SQLite file
- Existing `sql_security` validators and `execute_query_safely`
- Existing FastAPI + Pydantic stack on the server, existing Vite/TS tooling on the client
- No new third-party dependencies

## Testing

### Unit Tests

```bash
cd app/server && uv run pytest tests/test_table_crud.py -v
cd app/server && uv run pytest tests/test_sql_injection.py -v
cd app/server && uv run pytest
```

### Client Build / Typecheck

```bash
cd app/client && bun tsc --noEmit
cd app/client && bun run build
```

### E2E

Read `.claude/commands/test_e2e.md`, then execute `.claude/commands/e2e/test_data_preview_inline_editing.md`. The test covers opening the preview, paginating, editing a cell, adding a row, deleting a row, and verifying persistence across a page reload and the schema row-count update.

## Notes

- **Null vs empty string:** Cells rendered from `NULL` show as empty. Saving an empty input writes an empty string back, not NULL. SQLite will coerce to the column's affinity (e.g., empty for nullable INTEGER). This is acceptable for v1; a dedicated "set to NULL" affordance is future work.
- **Concurrency:** Last write wins. No optimistic locking. Out of scope for v1.
- **Identifier safety:** Table names, column names, and rowids are validated; injection attempts (`users; DROP TABLE users--`, etc.) return 400.
- **Future work:** column add/drop from the UI, bulk editing, type-aware cell editors (date pickers, etc.), undo/change history, and optimistic locking for concurrent edits.
- **Why a separate module:** `core/table_crud.py` keeps `server.py` thin (matching `sql_processor.py`, `insights.py`, `export_utils.py`) and lets row-level logic be unit-tested without spinning up FastAPI.
