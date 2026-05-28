# Feature: Data Preview with Inline Editing

## Metadata
issue_number: `45`
adw_id: `d9a18411`
issue_json: `{"number":45,"title":"3. Data Preview with Inline Editing","body":"/feature\n\nadw_sdlc_iso\n\nmodel_set heavy\n\nClick a table name in the schema panel to open a paginated preview (50 rows). Click any cell to edit it in place. Add or delete rows with buttons. Changes save back to SQLite.\n\n**Scope:**\n- Server: `GET /api/table/{name}/preview?page=1&limit=50`, `PATCH /api/table/{name}/row` (update), `POST /api/table/{name}/row` (insert), `DELETE /api/table/{name}/row/{rowid}` (delete)\n- Client: Preview modal with editable cells, add/delete row buttons, pagination\n\n**Acceptance criteria:**\n1. Clicking a table name opens a preview showing correct data with column headers\n2. Pagination works: page 2 shows different rows; \"Page X of Y\" is accurate\n3. Clicking a cell makes it editable; Enter saves; Escape reverts without saving\n4. Edited values persist after page refresh\n5. \"Add Row\" inserts a visible new row that persists after refresh\n6. \"Delete Row\" asks for confirmation, then removes the row permanently\n7. Schema panel row count updates after adding or deleting rows"}`

## Feature Description
A paginated, in-browser table editor for any uploaded SQLite table. Clicking a table name in the schema panel opens a modal showing 50 rows per page with column headers. Each cell becomes editable on click (Enter saves, Escape reverts). Buttons allow inserting a new row or deleting an existing row (with confirmation). All changes write through to SQLite, and the schema panel row count refreshes after structural changes.

This unlocks quick data inspection and cleanup workflows without forcing users to write SQL UPDATE/INSERT/DELETE statements, while preserving the same SQL injection protections used elsewhere in the app.

## User Story
As a data analyst working with uploaded CSV/JSON tables
I want to preview and edit table contents directly in the browser
So that I can fix typos, add missing rows, and clean up data without writing SQL by hand

## Problem Statement
Today, after uploading a CSV/JSON file the user can only run natural-language queries against the resulting SQLite table. There is no way to:
- See the actual contents of a table page by page
- Correct an obviously wrong value (typo, missing field, wrong unit)
- Add a single new record or delete a stale one

Users have to fix the source file and re-upload (which loses any other in-place changes), or hand-craft SQL through the natural-language interface and hope it generates the right statement.

## Solution Statement
Add four new server endpoints scoped to a single table:
- `GET /api/table/{name}/preview?page=1&limit=50` — paginated rows with rowid included for stable row identity
- `PATCH /api/table/{name}/row` — update a single cell, identified by rowid + column name
- `POST /api/table/{name}/row` — insert a new row with provided column values (empty/default if omitted)
- `DELETE /api/table/{name}/row/{rowid}` — delete by SQLite rowid

All endpoints route through the existing `sql_security` module (`validate_identifier`, `execute_query_safely`, `check_table_exists`) so they reuse the same injection guards. SQLite's implicit `rowid` is the row identifier — uploaded tables have no guaranteed primary key, so `rowid` is the most reliable handle.

On the client, the table name in the Available Tables list becomes a clickable element that opens a new "Preview Modal". The modal renders rows in a `<table>` where each `<td>` enters an in-place editing state on click; Enter commits via PATCH, Escape reverts. "+ Add Row" appends a blank row that gets persisted on first edit / commit. "Delete Row" appears per-row with a confirm dialog. Pagination controls (Prev / Next, "Page X of Y") drive the page query param. After successful add/delete, the schema panel reloads to reflect the updated row count.

## Relevant Files
Use these files to implement the feature:

### Server
- `app/server/server.py` — Add four new route handlers (`GET /api/table/{name}/preview`, `PATCH /api/table/{name}/row`, `POST /api/table/{name}/row`, `DELETE /api/table/{name}/row/{rowid}`). Follow the existing handler pattern: try/except, structured logging, return Pydantic response model.
- `app/server/core/data_models.py` — Add new Pydantic models: `TablePreviewResponse`, `UpdateRowRequest`, `InsertRowRequest`, `RowMutationResponse`.
- `app/server/core/sql_security.py` — Reuse `validate_identifier`, `execute_query_safely`, `check_table_exists` for identifier safety and parameterized execution. No changes expected — read only to confirm contract.
- `app/server/core/sql_processor.py` — Reference for how existing code uses `execute_query_safely` with `identifier_params`. No changes expected.
- `app/server/tests/test_sql_injection.py` — Pattern for writing security/regression tests with a `test_db` fixture. New tests for preview/CRUD endpoints will follow this style.

### New Server Files
- `app/server/core/table_crud.py` — New module that holds the row-level CRUD logic (`get_table_preview`, `update_row_cell`, `insert_row`, `delete_row`). Keeps `server.py` thin and matches the existing `core/*.py` pattern (`sql_processor.py`, `insights.py`, `export_utils.py`).
- `app/server/tests/test_table_crud.py` — Unit tests for the new `table_crud` module: pagination math, identifier rejection, rowid behavior, column validation, NULL handling.

### Client
- `app/client/index.html` — Add a hidden `<div id="preview-modal" class="modal">` with header (table name, close button), body (controls bar + table container + pagination bar), and footer. Mirror the existing `#upload-modal` structure.
- `app/client/src/main.ts` — Add `initializePreviewModal()` plus logic for opening the modal from a table name click, fetching pages, rendering editable cells, handling Add/Delete/Pagination. Update `displayTables()` so `tableName.textContent = table.name` becomes clickable (add `.table-name-clickable` class, `cursor: pointer`).
- `app/client/src/api/client.ts` — Add `getTablePreview`, `updateRowCell`, `insertRow`, `deleteRow` methods.
- `app/client/src/types.d.ts` — Add TS interfaces matching new Pydantic models: `TablePreviewResponse`, `UpdateRowRequest`, `InsertRowRequest`, `RowMutationResponse`.
- `app/client/src/style.css` — Add styles for preview modal (table layout, editable cell hover/focus state, pagination controls, Add Row / Delete Row buttons). Reuse existing CSS variables.

### Tests / Validation
- `.claude/commands/test_e2e.md` — Read to understand how E2E tests are executed by Playwright.
- `.claude/commands/e2e/test_basic_query.md` — Reference for the E2E test file format and step structure.
- `.claude/commands/e2e/test_export_functionality.md` — Reference for testing a modal-based feature with multiple interactions.

### New Test Files
- `.claude/commands/e2e/test_data_preview_inline_editing.md` — End-to-end Playwright test covering: open preview, paginate, edit a cell, add a row, delete a row, verify persistence after refresh, verify schema row count updates.

### Documentation Read
- `README.md` — Project overview and start/stop commands (required by `conditional_docs.md` when operating under `app/server` and `app/client`).

## Implementation Plan

### Phase 1: Foundation (Server data layer + models)
1. Define new Pydantic request/response models in `core/data_models.py`.
2. Create `core/table_crud.py` with row-level operations on top of `sql_security` helpers. Always use `rowid` to identify rows; always validate the table name and column names; always use parameterized values for cell content.
3. Add unit tests in `tests/test_table_crud.py` covering happy paths, pagination edges, missing table, invalid identifier, NULL cells, and rowid that doesn't exist.

### Phase 2: Core Implementation (Server endpoints + Client modal)
4. Wire the four new endpoints in `server.py`, delegating to `core/table_crud.py`. Mirror the existing handler shape (try/except, structured logging, Pydantic response, `HTTPException` for client errors).
5. Add the new HTTP methods on `api/client.ts` and the matching TS types in `types.d.ts`.
6. Add the Preview Modal HTML/CSS scaffolding.
7. Implement `initializePreviewModal()` in `main.ts`: open via table-name click, fetch page, render editable cells, handle in-place edit lifecycle, Add Row, Delete Row, pagination.

### Phase 3: Integration & Polish
8. Make the table name in the schema panel clickable; on click, open the modal scoped to that table.
9. After successful insert or delete, call `loadDatabaseSchema()` so the row count chip updates.
10. After successful PATCH/POST/DELETE, refresh the current modal page (so totals + pagination labels stay accurate).
11. Create the E2E test file and run it against the live app.
12. Run all validation commands; fix any regressions.

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

### Step 1: Add Pydantic models
- Edit `app/server/core/data_models.py`. At the bottom of the file (after `QueryExportRequest`), add:
  - `class TablePreviewRow(BaseModel)`: holds `rowid: int` and `values: Dict[str, Any]`.
  - `class TablePreviewResponse(BaseModel)`: `table_name: str`, `columns: List[str]`, `rows: List[TablePreviewRow]`, `page: int`, `limit: int`, `total_rows: int`, `total_pages: int`, `error: Optional[str] = None`.
  - `class UpdateRowRequest(BaseModel)`: `rowid: int`, `column: str`, `value: Optional[Any] = None`.
  - `class InsertRowRequest(BaseModel)`: `values: Dict[str, Any] = Field(default_factory=dict)`.
  - `class RowMutationResponse(BaseModel)`: `success: bool`, `rowid: Optional[int] = None`, `row_count: Optional[int] = None`, `error: Optional[str] = None`.

### Step 2: Create core/table_crud.py
- Create `app/server/core/table_crud.py`. Implement four functions, all of which:
  - Open `sqlite3.connect("db/database.db")`.
  - Call `validate_identifier(table_name, "table")` and `check_table_exists(conn, table_name)`; raise `HTTPException`-style errors via a custom `TableCRUDError` (or return error dicts) so `server.py` can translate them.
  - Use `execute_query_safely` with `identifier_params` for table/column names and `params` tuple for values.

- `get_table_preview(table_name: str, page: int, limit: int) -> dict`:
  - Clamp `page >= 1`, `1 <= limit <= 200`.
  - Query `SELECT COUNT(*) FROM {table}` to compute `total_rows` and `total_pages = max(1, ceil(total_rows / limit))`.
  - Query `PRAGMA table_info({table})` to get the ordered column list.
  - Query `SELECT rowid, * FROM {table} LIMIT ? OFFSET ?` with `(limit, (page - 1) * limit)`.
  - Return `{ "columns": [...], "rows": [{ "rowid": r, "values": {col: val, ...} }, ...], "page": page, "limit": limit, "total_rows": n, "total_pages": p }`.

- `update_row_cell(table_name: str, rowid: int, column: str, value: Any) -> dict`:
  - Validate `column` via `validate_identifier(column, "column")` AND verify it exists in `PRAGMA table_info(table)` (reject otherwise — prevents writing to non-existent columns).
  - Execute `UPDATE {table} SET {column} = ? WHERE rowid = ?` with `(value, rowid)`. Note: `execute_query_safely` only supports one `{ident}` template at a time — extend its `identifier_params` dict with both `table` and `column` keys (it already supports a dict, so this works).
  - Confirm `cursor.rowcount == 1`; otherwise return `{"success": False, "error": "Row not found"}`.
  - Return `{"success": True, "rowid": rowid}`.

- `insert_row(table_name: str, values: Dict[str, Any]) -> dict`:
  - Get column list via `PRAGMA table_info(table)`.
  - If `values` is empty, run `INSERT INTO {table} DEFAULT VALUES`.
  - Otherwise: validate every key in `values` via `validate_identifier(col, "column")` and verify it's in the column list. Build `INSERT INTO {table} ({col_list}) VALUES (?, ?, ...)` where the column identifiers are escaped via `escape_identifier`, then parameterize the values tuple.
  - `conn.commit()`; return `{"success": True, "rowid": cursor.lastrowid}`.

- `delete_row(table_name: str, rowid: int) -> dict`:
  - Execute `DELETE FROM {table} WHERE rowid = ?` with `(rowid,)`.
  - If `cursor.rowcount == 0`, return `{"success": False, "error": "Row not found"}`.
  - Return `{"success": True}`.

- Use `with sqlite3.connect(...)` or explicit close in `finally`. Set `conn.row_factory = sqlite3.Row` for the preview SELECT so we can produce a dict per row.

### Step 3: Wire endpoints in server.py
- Edit `app/server/server.py`. Add imports for the new models from `core.data_models` and the new functions from `core.table_crud`.
- Add four handlers, each following the existing pattern (try/except, structured logging on success and error, `HTTPException` for 400/404, generic 500 fallback):

  ```python
  @app.get("/api/table/{table_name}/preview", response_model=TablePreviewResponse)
  async def get_table_preview_endpoint(table_name: str, page: int = 1, limit: int = 50):
      ...

  @app.patch("/api/table/{table_name}/row", response_model=RowMutationResponse)
  async def update_table_row(table_name: str, request: UpdateRowRequest):
      ...

  @app.post("/api/table/{table_name}/row", response_model=RowMutationResponse)
  async def insert_table_row(table_name: str, request: InsertRowRequest):
      ...

  @app.delete("/api/table/{table_name}/row/{rowid}", response_model=RowMutationResponse)
  async def delete_table_row(table_name: str, rowid: int):
      ...
  ```

- Translate `SQLSecurityError` / `TableCRUDError` to `HTTPException(400, ...)` and "not found" cases to `HTTPException(404, ...)`. Log with the same `[SUCCESS]` / `[ERROR]` style used by other handlers.

### Step 4: Add server unit tests
- Create `app/server/tests/test_table_crud.py`. Pattern after `tests/test_sql_injection.py`:
  - `test_db` fixture that creates a temp SQLite DB with a `widgets` table (id, name, qty), inserts a few rows, monkeypatches the `db/database.db` path used by `core/table_crud` (or accept `db_path` as a parameter to ease testing).
  - Tests: `test_preview_returns_paginated_rows`, `test_preview_includes_rowid_for_each_row`, `test_preview_total_pages_calculation`, `test_preview_invalid_table_name_raises`, `test_preview_missing_table_raises`, `test_update_cell_updates_value`, `test_update_cell_invalid_column_raises`, `test_update_cell_missing_rowid_returns_error`, `test_insert_row_with_values`, `test_insert_row_default_values`, `test_insert_row_returns_rowid`, `test_insert_row_invalid_column_raises`, `test_delete_row_removes_record`, `test_delete_row_missing_rowid_returns_error`.
- Decide on testability approach: easiest is to accept an optional `db_path` argument on the `table_crud` functions (default `"db/database.db"`) so tests can point at the temp file.

### Step 5: Add TypeScript types
- Edit `app/client/src/types.d.ts`. Append:
  ```ts
  interface TablePreviewRow { rowid: number; values: Record<string, any>; }
  interface TablePreviewResponse {
    table_name: string;
    columns: string[];
    rows: TablePreviewRow[];
    page: number;
    limit: number;
    total_rows: number;
    total_pages: number;
    error?: string;
  }
  interface UpdateRowRequest { rowid: number; column: string; value: any; }
  interface InsertRowRequest { values: Record<string, any>; }
  interface RowMutationResponse { success: boolean; rowid?: number; row_count?: number; error?: string; }
  ```

### Step 6: Add API client methods
- Edit `app/client/src/api/client.ts`. Inside the `api` object add:
  - `getTablePreview(tableName, page = 1, limit = 50): Promise<TablePreviewResponse>` — GET `/table/${encodeURIComponent(tableName)}/preview?page=${page}&limit=${limit}`.
  - `updateRowCell(tableName, request: UpdateRowRequest): Promise<RowMutationResponse>` — PATCH `/table/${encodeURIComponent(tableName)}/row` with JSON body.
  - `insertRow(tableName, request: InsertRowRequest): Promise<RowMutationResponse>` — POST `/table/${encodeURIComponent(tableName)}/row` with JSON body.
  - `deleteRow(tableName, rowid: number): Promise<RowMutationResponse>` — DELETE `/table/${encodeURIComponent(tableName)}/row/${rowid}`.

### Step 7: Add preview modal HTML
- Edit `app/client/index.html`. After the existing `#upload-modal` block, add a new modal:
  ```html
  <div id="preview-modal" class="modal" style="display: none;">
    <div class="modal-content preview-modal-content">
      <div class="modal-header">
        <h2 id="preview-modal-title">Preview Table</h2>
        <button class="close-modal close-preview-modal">&times;</button>
      </div>
      <div class="modal-body">
        <div class="preview-toolbar">
          <button id="add-row-button" class="primary-button">+ Add Row</button>
          <span id="preview-status" class="preview-status"></span>
        </div>
        <div id="preview-table-container" class="preview-table-container"></div>
        <div class="preview-pagination">
          <button id="preview-prev" class="secondary-button">Prev</button>
          <span id="preview-page-label">Page 1 of 1</span>
          <button id="preview-next" class="secondary-button">Next</button>
        </div>
      </div>
    </div>
  </div>
  ```

### Step 8: Add CSS for preview modal
- Edit `app/client/src/style.css`. Add styles for:
  - `.preview-modal-content` — wider than upload modal (e.g., `max-width: 90vw`), tall content area.
  - `.preview-toolbar` — flex row, space-between, with `#add-row-button` on the left and `#preview-status` on the right.
  - `.preview-table-container` — scrollable container, `max-height: 60vh`, `overflow: auto`.
  - `.preview-table` — full width, header sticky.
  - `.preview-table td.editable` — `cursor: pointer`, subtle hover (`background: rgba(...)`); selected/editing cell shows an `<input>` styled to fit.
  - `.preview-table td.delete-cell` — narrow, contains the per-row delete button.
  - `.delete-row-button` — small destructive button.
  - `.preview-pagination` — centered flex row, gap, with prev/next + page label.
  - `.table-name-clickable` — adds `cursor: pointer` and underline-on-hover styling for the table name.

### Step 9: Implement preview modal logic in main.ts
- Edit `app/client/src/main.ts`. Add module-level state for the open preview: `currentPreview: { tableName: string; page: number; limit: number; totalPages: number; columns: string[]; rows: TablePreviewRow[] } | null = null;`.
- Add `initializePreviewModal()`:
  - Wire close button + background click to close (mirror `initializeModal`).
  - Wire `#preview-prev` and `#preview-next` to change page and `loadPreviewPage()`.
  - Wire `#add-row-button` to call `api.insertRow(currentPreview.tableName, { values: {} })`, then jump to the last page and `loadPreviewPage()` + `loadDatabaseSchema()`.
- Add `openPreview(tableName: string)`:
  - Set `currentPreview = { tableName, page: 1, limit: 50, ... }`.
  - Show the modal, set `#preview-modal-title` to "Preview: {tableName}".
  - Call `loadPreviewPage()`.
- Add `loadPreviewPage()`:
  - Call `api.getTablePreview(currentPreview.tableName, currentPreview.page, currentPreview.limit)`.
  - Update `currentPreview.totalPages`, `.columns`, `.rows`.
  - Render the table into `#preview-table-container` via `renderPreviewTable()`.
  - Update `#preview-page-label` to `Page {page} of {totalPages}`.
  - Update `#preview-status` to `{total_rows} rows total`.
  - Disable Prev when `page === 1`, disable Next when `page === totalPages`.
- Add `renderPreviewTable(columns, rows)`:
  - Build a `<table class="preview-table">` with `<thead>` showing each column name plus an empty header for the delete-cell column.
  - For each row, render a `<tr data-rowid="{rowid}">` with one `<td class="editable" data-column="{col}">` per column (text content of the cell value, or empty string if null), plus a final `<td class="delete-cell">` containing a "Delete" button.
  - Attach click handler on each editable td: replace its content with an `<input>` prefilled with the current value, focus, select. On `Enter`: PATCH via `api.updateRowCell(tableName, { rowid, column, value: input.value })`; on success replace input with new value; on failure show error and revert. On `Escape`: revert to original content. On blur: same as Escape (revert without saving) to keep the contract predictable.
  - The "Delete" button asks `confirm("Delete this row?")` then calls `api.deleteRow(tableName, rowid)`. On success: `loadPreviewPage()` (adjusts current page if it now points past the end) and `loadDatabaseSchema()` to refresh schema row count.
- Update `displayTables()` (around line 322): when creating `tableName` div, add class `table-name-clickable` and an `onclick` that calls `openPreview(table.name)`.
- Add `initializePreviewModal()` to the `DOMContentLoaded` handler at the top of the file.

### Step 10: Refresh schema after mutations
- After successful `insertRow`: call `loadDatabaseSchema()` so the row count chip updates immediately.
- After successful `deleteRow`: call `loadDatabaseSchema()` for the same reason.
- After cell PATCH: row count does not change, no schema refresh needed.

### Step 11: Create E2E test file
- Create `.claude/commands/e2e/test_data_preview_inline_editing.md` modeled on `.claude/commands/e2e/test_basic_query.md` and `.claude/commands/e2e/test_export_functionality.md`. Steps should cover, at minimum:
  1. Navigate to the app.
  2. Load the `users` sample data (so we have a known table with > 1 row).
  3. **Verify** the table name "users" is clickable in the Available Tables list.
  4. Click the table name. Take a screenshot of the open preview modal.
  5. **Verify** the modal shows the column headers and row data.
  6. **Verify** pagination label reads `Page 1 of 1` (since users sample is 20 rows, fits in one page). Take a screenshot.
  7. Click any cell (e.g., the first row's `name`). **Verify** an input field appears.
  8. Type a new value, press Enter. **Verify** the cell updates to the new value. Take a screenshot.
  9. Click `+ Add Row`. **Verify** a new row appears and that the "X rows total" status increments by 1.
  10. Close and re-open the modal. **Verify** the edit and the new row persist.
  11. Click `Delete` on the newly added row, confirm the dialog. **Verify** the row disappears and the status decrements.
  12. Close the modal. **Verify** the schema panel row count for `users` matches the new total.
- Use the same Output Format and Success Criteria conventions as the other E2E files.

### Step 12: Manual sanity check via README commands
- Start the app per `README.md`: `./scripts/start.sh`.
- Manually run through the steps in the new E2E test to confirm the feature works before letting automation grade it.

### Step 13: Run validation commands
- Run every command in the `Validation Commands` section below. Fix any failures and re-run until all pass.

## Testing Strategy

### Unit Tests (server, `tests/test_table_crud.py`)
- Preview returns the requested page slice with `rowid` included for every row.
- Preview's `total_pages` math is correct for empty tables, exactly-one-page tables, and overflow.
- Update succeeds on a valid rowid + column and persists across a fresh connection.
- Update on an unknown rowid returns `success=False` with a clear message and does not raise.
- Update on an unknown column raises (rejected by `validate_identifier` and/or `PRAGMA` check).
- Insert with values persists and returns a usable `rowid`.
- Insert with empty `values` uses `DEFAULT VALUES`.
- Insert with a non-existent column key raises.
- Delete removes exactly one row and persists.
- Delete on a missing rowid returns `success=False`.
- Identifier injection in `table_name` (e.g., `users; DROP TABLE users--`) is rejected.

### E2E Test
- `test_data_preview_inline_editing.md` covers the full UI flow including persistence after refresh, pagination labels, and schema row count refresh.

### Edge Cases
- Empty table: preview returns zero rows, `total_pages = 1`, "Page 1 of 1", Prev/Next disabled. Insert still works.
- Single-page table: Next disabled.
- Last-page deletion that empties the page: client recomputes current page (`page = min(page, total_pages)`) after refetch.
- NULL cell values: render as empty string; on save, sending an empty input writes an empty string (NOT null) — document this behavior; if the column was nullable INTEGER and the user submits empty, SQLite will coerce, which is acceptable for v1.
- Special characters in cell values (quotes, semicolons): handled by parameterized queries, no special quoting on the client.
- Table names with spaces or underscores: pass through `validate_identifier` (already allows alphanumerics + underscores + spaces) and URL-encode on the client.
- Concurrent edits: out of scope for v1; last write wins.

## Acceptance Criteria
1. Clicking a table name in the Available Tables list opens a modal preview that shows that table's data with column headers in the original column order. ✅
2. With > 50 rows, switching to Page 2 shows a different set of rows, and the "Page X of Y" label reflects the correct totals. ✅
3. Clicking any cell turns it into an `<input>` prefilled with the current value. Pressing Enter saves; pressing Escape (or blurring) reverts without saving. ✅
4. After editing a cell and reloading the browser page, the new value is still present in the preview. ✅
5. Clicking "+ Add Row" inserts a new row that is immediately visible and is still present after refreshing the browser. ✅
6. Clicking "Delete" prompts for confirmation; cancelling leaves the row intact; confirming permanently removes it. ✅
7. After insert or delete, the Available Tables panel's row count chip for that table reflects the new total without a manual refresh. ✅
8. All operations route through `sql_security`; injection attempts via table name, column name, or rowid are rejected with a 400. ✅
9. Server tests and client typecheck/build all pass. ✅

## Validation Commands
Execute every command to validate the feature works correctly with zero regressions.

- `cd app/server && uv run pytest` — Run all server tests, including the new `test_table_crud.py` and existing security tests; expect 0 failures.
- `cd app/server && uv run pytest tests/test_table_crud.py -v` — Run new CRUD tests in verbose mode for a focused signal.
- `cd app/server && uv run pytest tests/test_sql_injection.py -v` — Confirm existing security tests still pass; the new endpoints must not regress injection protection.
- `cd app/client && bun tsc --noEmit` — Typecheck the client; expect no errors.
- `cd app/client && bun run build` — Build the client; expect a clean build with no warnings about missing types.
- Read `.claude/commands/test_e2e.md`, then read and execute `.claude/commands/e2e/test_data_preview_inline_editing.md` to validate the full UI flow against the live app.
- Read `.claude/commands/test_e2e.md`, then read and execute `.claude/commands/e2e/test_basic_query.md` to confirm core query flow still works (regression check).
- Read `.claude/commands/test_e2e.md`, then read and execute `.claude/commands/e2e/test_export_functionality.md` to confirm the other modal-based feature still works (regression check).

## Notes
- **Rowid choice:** Uploaded tables are created from CSV/JSON without an explicit `INTEGER PRIMARY KEY`, so they have no stable user-facing PK. SQLite's implicit `rowid` is the most reliable handle. We surface it only in API payloads, not in the rendered cell grid (it's stored on the `<tr data-rowid>` attribute).
- **Identifier safety extension:** `execute_query_safely` already supports a dict of `identifier_params`, so passing `{"table": table_name, "column": column_name}` works for the UPDATE statement — no changes needed to `sql_security.py`.
- **Pagination clamping:** Both server (clamp `page >= 1`, `1 <= limit <= 200`) and client (`page = min(max(1, page), totalPages)`) clamp, so a deletion that empties the last page recovers gracefully.
- **No new third-party dependencies** are needed on either server or client; everything is built with stdlib + FastAPI + existing Vite/TS tooling.
- **Future work (out of scope):**
  - Adding a column / dropping a column from the UI.
  - Bulk editing.
  - Type-aware cell editors (e.g., date picker for DATE columns).
  - Undo / change history.
  - Optimistic locking for concurrent edits.
- **Why a separate `core/table_crud.py` module:** keeps `server.py` thin (matches the existing pattern with `sql_processor.py`, `insights.py`, `export_utils.py`) and lets us unit test row-level logic without spinning up FastAPI.
