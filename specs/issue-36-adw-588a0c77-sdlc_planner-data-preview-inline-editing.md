# Feature: Data Preview with Inline Editing

## Metadata
issue_number: `36`
adw_id: `588a0c77`
issue_json: `{"number":36,"title":"Data Preview with Inline Editing","body":"/feature\n\nadw_sdlc_iso\n\nmodel_set heavy\n\nClick a table name in the schema panel to open a paginated preview (50 rows). Click any cell to edit it in place. Add or delete rows with buttons. Changes save back to SQLite.\n\n**Scope:**\n- Server: GET /api/table/{name}/preview?page=1&limit=50, PATCH /api/table/{name}/row (update), POST /api/table/{name}/row (insert), DELETE /api/table/{name}/row/{rowid} (delete)\n- Client: Preview modal with editable cells, add/delete row buttons, pagination\n\n**Acceptance criteria:**\n1. Clicking a table name opens a preview showing correct data with column headers\n2. Pagination works: page 2 shows different rows; \"Page X of Y\" is accurate\n3. Clicking a cell makes it editable; Enter saves; Escape reverts without saving\n4. Edited values persist after page refresh\n5. \"Add Row\" inserts a visible new row that persists after refresh\n6. \"Delete Row\" asks for confirmation, then removes the row permanently\n7. Schema panel row count updates after adding or deleting rows\n"}`

## Feature Description
Add a data preview and inline editing experience to the Natural Language SQL Interface. Users currently can see only table metadata (name, row count, column tags) in the **Available Tables** section, with no way to inspect or modify the underlying rows directly. This feature lets a user click a table name to open a paginated preview modal (50 rows per page), edit any cell in place, add new rows, and delete existing rows — with all changes persisted to SQLite. This brings basic spreadsheet-style data management to the app without leaving the browser, complementing the existing natural-language query path.

## User Story
As a data analyst using the Natural Language SQL Interface
I want to preview, edit, add, and delete rows in any uploaded table directly from the UI
So that I can quickly fix data quality issues, add missing records, or experiment with different values without writing SQL or re-uploading files

## Problem Statement
Today, after uploading a CSV/JSON file, the only ways to interact with table data are (a) running a natural-language query, or (b) deleting/exporting the table. There is no way to:
- Browse the actual rows of a table page-by-page,
- Fix a single bad value (typo, wrong number, etc.),
- Add a missing row, or
- Remove a single offending row.

The schema panel shows only metadata, and re-uploading a corrected file is the only way to update data. This is slow, error-prone, and breaks the workflow for users iterating on small data sets.

## Solution Statement
Introduce a **table preview modal** triggered by clicking a table name in the **Available Tables** section. The modal displays 50 rows at a time with previous/next pagination controls and a "Page X of Y" indicator. Each data cell becomes an `<input>` on click; pressing Enter saves the change via a `PATCH` endpoint, and Escape reverts. An **Add Row** button inserts a blank row that the user fills in (persisted via `POST`); a **Delete Row** button on each row prompts for confirmation and then removes it via `DELETE`. After any mutation, the schema panel is refreshed so the row count stays accurate.

On the server, four new endpoints are added under `/api/table/{table_name}/...` that use the existing `core/sql_security.py` helpers (`validate_identifier`, `execute_query_safely`) to safely build parameterized UPDATE/INSERT/DELETE statements. Rows are addressed by SQLite's built-in `rowid` (always present, even for user-uploaded tables without an explicit primary key) which is included in every preview response.

## Relevant Files
Use these files to implement the feature:

### Server
- `app/server/server.py` — Main FastAPI app; current routes follow the pattern of `DELETE /api/table/{table_name}` (lines 275-310) and `POST /api/export/table` (lines 312-344). Add the four new preview/CRUD endpoints here.
- `app/server/core/data_models.py` — Pydantic request/response models. Add models for the preview response, row update/insert/delete operations.
- `app/server/core/sql_security.py` — Already provides `validate_identifier`, `escape_identifier`, `execute_query_safely`, `check_table_exists`. The existing `execute_query_safely` permits UPDATE/INSERT/DELETE without `allow_ddl=True` (DDL list is DROP/CREATE/ALTER/TRUNCATE), so DML is safe to use directly. Add a helper `get_table_columns(conn, table_name)` if needed (or reuse `PRAGMA table_info` pattern from `sql_processor.py`).
- `app/server/core/sql_processor.py` — Reference pattern for `PRAGMA table_info({table})` and connection management; mirror the connection style for the new endpoints.
- `app/server/tests/test_sql_injection.py` — Reference for pytest fixture patterns (temporary SQLite DB, `@patch('core.sql_processor.sqlite3.connect')`).
- `app/server/tests/core/test_sql_processor.py` — Existing structural pattern for testing core modules.

### Client
- `app/client/index.html` — Contains the existing upload modal (lines 50-96) as a template. Add a new `#preview-modal` markup with header (table name + close), pagination controls, table area, action buttons.
- `app/client/src/main.ts` — Houses all client logic. The schema panel render lives in `displayTables()` (lines 296-387) — wire a click handler on `tableName` to open the preview. Existing `createResultsTable()` (lines 265-293) is the reference for building tables; extend the pattern to render an editable preview table. Modal show/hide pattern is in `initializeModal()` (lines 433-463). Reuse `removeTable()` (lines 465-505) confirmation/refresh pattern for row delete.
- `app/client/src/api/client.ts` — Centralized `apiRequest<T>` wrapper plus `api` object. Add `getTablePreview`, `updateRow`, `insertRow`, `deleteRow` methods following existing typed patterns.
- `app/client/src/types.d.ts` — TypeScript interfaces matching Pydantic models. Add `TablePreviewResponse`, `RowUpdateRequest`, `RowInsertRequest`, `RowMutationResponse`.
- `app/client/src/style.css` — Add styles for preview modal, editable cells (hover/focus state), pagination controls, action buttons. Reference `.modal`, `.results-table`, `.primary-button`, `.secondary-button`.

### Documentation & E2E test conventions (read-only references)
- `README.md` — Project overview; you are operating on `app/server` and `app/client`, so read this for project structure and start commands.
- `.claude/commands/conditional_docs.md` — Maps tasks to relevant docs; nothing matches this feature beyond the README baseline (no CSV export / no LLM model / no styling-theme-only changes).
- `.claude/commands/test_e2e.md` — E2E runner format (Playwright via MCP, screenshot directory conventions, JSON output schema).
- `.claude/commands/e2e/test_basic_query.md` — Example E2E test format (User Story, Test Steps with **Verify**, Success Criteria).
- `.claude/commands/e2e/test_complex_query.md` — A second example for additional E2E format reference.

### New Files
- `specs/issue-36-adw-588a0c77-sdlc_planner-data-preview-inline-editing.md` — This plan file.
- `app/server/tests/test_table_rows.py` — New pytest module covering the four new endpoints (preview pagination, row update, insert, delete) and security/edge cases (invalid identifiers, missing tables, non-existent rowid).
- `.claude/commands/e2e/test_data_preview_inline_editing.md` — New Playwright E2E test file validating the full UI flow (open modal, paginate, edit cell, add row, delete row, confirm row count refresh).

## Implementation Plan

### Phase 1: Foundation (Server-side data layer)
Add Pydantic models and four new FastAPI endpoints. All endpoints validate the table name with `validate_identifier`, check existence with `check_table_exists`, and run parameterized queries via `execute_query_safely`. Rows are uniquely identified by SQLite's implicit `rowid` returned in every preview row. INSERT uses dynamic placeholders for the column list; UPDATE uses dynamic `SET col = ?` clauses; DELETE uses `WHERE rowid = ?`. Add server unit tests covering the happy path, invalid identifiers, missing tables, and non-existent rowids.

### Phase 2: Core Implementation (Client preview modal & inline editing)
Add a new preview modal to `index.html` and the supporting logic in `main.ts`. Wire a click handler on each schema-panel table name to call `api.getTablePreview()` and open the modal. Render the response as an HTML table where each cell is wrapped in a span that, when clicked, replaces itself with an `<input>` pre-filled with the cell value; pressing Enter calls `api.updateRow()` and reverts to a span on success; Escape reverts without saving. Add **Add Row** (creates an inline blank row that lets the user type values; on first Enter or "Save" click calls `api.insertRow()`) and **Delete** (per-row icon button using `confirm()` then `api.deleteRow()`). Add **Previous / Next** pagination buttons and a "Page X of Y" indicator wired to re-fetch with the new page number. Add types in `types.d.ts` and methods in `api/client.ts`. Style the modal in `style.css`.

### Phase 3: Integration (Schema panel refresh, E2E validation)
After every successful insert/delete, call the existing `loadDatabaseSchema()` so the schema panel's row count stays in sync (acceptance criterion #7). Add an E2E test file and run the full validation suite (server pytest, client tsc, client build, manual E2E run) to confirm zero regressions.

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

### Step 1: Add Pydantic models for table-row operations
- Open `app/server/core/data_models.py`.
- At the end of the file, add the following models:
  - `TablePreviewRow(BaseModel)` — fields: `rowid: int`, `data: Dict[str, Any]` (column → value).
  - `TablePreviewResponse(BaseModel)` — fields: `table_name: str`, `columns: List[str]`, `rows: List[TablePreviewRow]`, `page: int`, `limit: int`, `total_rows: int`, `total_pages: int`, `error: Optional[str] = None`.
  - `RowUpdateRequest(BaseModel)` — fields: `rowid: int`, `updates: Dict[str, Any]` (column name → new value).
  - `RowInsertRequest(BaseModel)` — fields: `data: Dict[str, Any]` (column name → value; allow partial — missing columns default to NULL).
  - `RowMutationResponse(BaseModel)` — fields: `success: bool`, `rowid: Optional[int] = None` (the affected/new rowid), `row_count: int` (table's new total row count after the mutation), `error: Optional[str] = None`.

### Step 2: Add `GET /api/table/{table_name}/preview` endpoint
- Open `app/server/server.py`.
- Import the new models from `core.data_models`.
- After the existing `delete_table` route (around line 310), add a new endpoint:
  - Path: `GET /api/table/{table_name}/preview`
  - Query params: `page: int = 1`, `limit: int = 50`. Clamp `limit` to `[1, 200]` and `page` to `>= 1`.
  - Validate `table_name` with `validate_identifier`; return 400 on `SQLSecurityError`.
  - Connect via `sqlite3.connect("db/database.db")` with `conn.row_factory = sqlite3.Row`.
  - Verify table exists via `check_table_exists`; return 404 if missing.
  - Get column names using `execute_query_safely(conn, "PRAGMA table_info({table})", identifier_params={'table': table_name})` and extract `col[1]` for each row.
  - Get total row count using `execute_query_safely(conn, "SELECT COUNT(*) FROM {table}", identifier_params={'table': table_name})`.
  - Compute `offset = (page - 1) * limit` and `total_pages = max(1, ceil(total_rows / limit))`.
  - Fetch the page using `execute_query_safely(conn, "SELECT rowid, * FROM {table} ORDER BY rowid LIMIT ? OFFSET ?", params=(limit, offset), identifier_params={'table': table_name})`.
  - Build `TablePreviewRow` objects: extract `rowid` from each row and put the rest of the columns into `data`.
  - Close connection; return `TablePreviewResponse`.
  - Wrap in try/except: log errors and return a `TablePreviewResponse` with `error=str(e)` (consistent with other endpoints).

### Step 3: Add `PATCH /api/table/{table_name}/row` endpoint
- In `app/server/server.py`, add an endpoint after the preview route:
  - Path: `PATCH /api/table/{table_name}/row`
  - Body: `RowUpdateRequest`.
  - Validate `table_name` with `validate_identifier`.
  - Connect, verify table exists.
  - Get the table's column list via `PRAGMA table_info`. For each key in `request.updates`, validate it via `validate_identifier(key, "column")` AND verify it exists in the column list (return 400 with a clear error otherwise).
  - Reject empty `updates` dict with 400.
  - Build SET clause dynamically: for each column in `updates`, append `{col_N} = ?` to the query and add the value to `params`. Use `identifier_params` to map each placeholder to the validated column name (e.g., `identifier_params={'table': table_name, 'col_0': 'name', 'col_1': 'age', ...}`).
  - Execute: `UPDATE {table} SET {col_0} = ?, {col_1} = ? WHERE rowid = ?` with `params=(*update_values, rowid)`.
  - `conn.commit()`.
  - Verify `cursor.rowcount == 1`; if 0, return 404 (row not found).
  - Re-query `SELECT COUNT(*) FROM {table}` for `row_count`.
  - Return `RowMutationResponse(success=True, rowid=request.rowid, row_count=...)`.

### Step 4: Add `POST /api/table/{table_name}/row` endpoint
- In `app/server/server.py`, add an endpoint:
  - Path: `POST /api/table/{table_name}/row`
  - Body: `RowInsertRequest`.
  - Validate `table_name` with `validate_identifier`.
  - Verify table exists.
  - Get the column list from `PRAGMA table_info`. For each key in `request.data`, validate via `validate_identifier(key, "column")` AND verify it exists in the column list. Allow `request.data` to be empty (inserts a row with all NULLs / defaults — useful for "Add Row" UI).
  - Build the INSERT dynamically:
    - If `data` is empty: `INSERT INTO {table} DEFAULT VALUES`.
    - Otherwise: `INSERT INTO {table} ({col_0}, {col_1}, ...) VALUES (?, ?, ...)` with values list, using `identifier_params` to safely interpolate each column.
  - `conn.commit()`.
  - Capture `cursor.lastrowid` as the new rowid.
  - Re-query row count.
  - Return `RowMutationResponse(success=True, rowid=new_rowid, row_count=...)`.

### Step 5: Add `DELETE /api/table/{table_name}/row/{rowid}` endpoint
- In `app/server/server.py`, add an endpoint:
  - Path: `DELETE /api/table/{table_name}/row/{rowid}`
  - Path params: `table_name: str`, `rowid: int`.
  - Validate `table_name` with `validate_identifier`.
  - Verify table exists.
  - Execute: `execute_query_safely(conn, "DELETE FROM {table} WHERE rowid = ?", params=(rowid,), identifier_params={'table': table_name})`.
  - `conn.commit()`.
  - Verify `cursor.rowcount == 1`; if 0, return 404.
  - Re-query row count.
  - Return `RowMutationResponse(success=True, rowid=rowid, row_count=...)`.

### Step 6: Add server unit tests for the new endpoints
- Create `app/server/tests/test_table_rows.py`.
- Use `fastapi.testclient.TestClient` with the FastAPI `app` from `server.py`.
- Add a pytest fixture that:
  - Creates a temporary `db/database.db` (or monkey-patches the path) with a small test table (e.g., `users` with columns `id INTEGER, name TEXT, age INTEGER`).
  - Inserts ~75 rows so pagination is meaningful (page 1 = 50 rows, page 2 = 25 rows).
  - Yields the client, then cleans up the database file.
- Test cases:
  - `test_preview_page_1_returns_50_rows` — returns 50 rows, total_rows=75, total_pages=2, page=1.
  - `test_preview_page_2_returns_remaining_rows` — page=2 returns rows 51-75.
  - `test_preview_invalid_table_name_400` — `GET /api/table/DROP TABLE/preview` → 400.
  - `test_preview_missing_table_404` — non-existent table → 404.
  - `test_update_row_persists_change` — PATCH with `{rowid: 1, updates: {name: "Updated"}}` changes the row and `SELECT name FROM users WHERE rowid=1` returns "Updated".
  - `test_update_row_rejects_unknown_column` — PATCH with non-existent column → 400.
  - `test_update_row_not_found` — PATCH with non-existent rowid → 404.
  - `test_insert_row_creates_visible_row` — POST then GET preview; confirm new row count and the new value is present.
  - `test_insert_row_with_empty_data` — POST with `{data: {}}` succeeds (inserts NULL defaults).
  - `test_delete_row_removes_row` — DELETE then preview; total_rows decreased by 1.
  - `test_delete_nonexistent_row_404` — DELETE with non-existent rowid → 404.
  - `test_sql_injection_in_table_name_blocked` — `GET /api/table/users; DROP TABLE users/preview` → 400.

### Step 7: Add TypeScript interfaces
- Open `app/client/src/types.d.ts`.
- Add the following interfaces (mirroring Pydantic models exactly):
  - `TablePreviewRow { rowid: number; data: Record<string, any>; }`
  - `TablePreviewResponse { table_name: string; columns: string[]; rows: TablePreviewRow[]; page: number; limit: number; total_rows: number; total_pages: number; error?: string; }`
  - `RowUpdateRequest { rowid: number; updates: Record<string, any>; }`
  - `RowInsertRequest { data: Record<string, any>; }`
  - `RowMutationResponse { success: boolean; rowid?: number; row_count: number; error?: string; }`

### Step 8: Add API client methods
- Open `app/client/src/api/client.ts`.
- Add to the `api` object:
  - `getTablePreview(tableName: string, page: number = 1, limit: number = 50): Promise<TablePreviewResponse>` — `GET /table/{tableName}/preview?page=...&limit=...`.
  - `updateRow(tableName: string, request: RowUpdateRequest): Promise<RowMutationResponse>` — `PATCH /table/{tableName}/row` with JSON body.
  - `insertRow(tableName: string, request: RowInsertRequest): Promise<RowMutationResponse>` — `POST /table/{tableName}/row` with JSON body.
  - `deleteRow(tableName: string, rowid: number): Promise<RowMutationResponse>` — `DELETE /table/{tableName}/row/{rowid}`.
- Use `encodeURIComponent(tableName)` in the URL path (defense-in-depth — server still validates).

### Step 9: Add preview modal markup to `index.html`
- Open `app/client/index.html`.
- After the upload modal `<div id="upload-modal">`, add a new modal `<div id="preview-modal" class="modal" style="display: none;">` containing:
  - `<div class="modal-content modal-content-wide">` (a new wider variant; we'll style it).
  - `<div class="modal-header">` with `<h2 id="preview-modal-title">Table Preview</h2>` and `<button class="close-modal close-preview-modal">&times;</button>`.
  - `<div class="modal-body">`:
    - `<div class="preview-toolbar">` containing an **Add Row** button (`#preview-add-row-button` — primary), a **Previous** button (`#preview-prev-page` — secondary), `<span id="preview-page-indicator">Page 1 of 1</span>`, a **Next** button (`#preview-next-page` — secondary).
    - `<div id="preview-error" class="error-message" style="display: none;"></div>`.
    - `<div id="preview-table-container">` (the table will be rendered into here).

### Step 10: Add styles for the preview modal
- Open `app/client/src/style.css`.
- Add:
  - `.modal-content-wide { max-width: 1100px; width: 95%; max-height: 90vh; overflow: auto; }`
  - `.preview-toolbar { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem; }`
  - `.preview-toolbar .preview-spacer { flex: 1; }`
  - `.preview-table { width: 100%; border-collapse: collapse; }` (mirroring `.results-table`).
  - `.preview-table th, .preview-table td { padding: 0.5rem; border-bottom: 1px solid var(--border-color, #ddd); text-align: left; }`
  - `.preview-cell { cursor: pointer; min-width: 4rem; display: inline-block; }`
  - `.preview-cell:hover { background: rgba(0, 123, 255, 0.08); }`
  - `.preview-cell-input { width: 100%; padding: 0.25rem 0.5rem; box-sizing: border-box; font: inherit; }`
  - `.preview-row-actions { white-space: nowrap; }`
  - `.preview-delete-row { background: transparent; border: none; cursor: pointer; color: #c00; font-size: 1.1rem; }`
  - `.preview-add-row { background: rgba(40, 167, 69, 0.08); }` (visual hint for the new uncommitted row).
  - `.table-name { cursor: pointer; }` and `.table-name:hover { text-decoration: underline; }`.

### Step 11: Wire up the click handler on table names
- Open `app/client/src/main.ts`.
- In `displayTables()`, after creating `tableName` (around line 322), add:
  - `tableName.title = "Click to preview and edit rows";`
  - `tableName.addEventListener('click', (e) => { e.stopPropagation(); openPreviewModal(table.name); });`
- Add `e.stopPropagation()` defensively so clicks don't bubble to other table-item handlers.

### Step 12: Implement the preview modal logic
- In `app/client/src/main.ts`, add module-level state:
  ```ts
  let previewState: {
    tableName: string;
    page: number;
    limit: number;
    columns: string[];
    rows: TablePreviewRow[];
    totalPages: number;
  } | null = null;
  ```
- Add `function openPreviewModal(tableName: string)`:
  - Sets `previewState = { tableName, page: 1, limit: 50, columns: [], rows: [], totalPages: 1 }`.
  - Sets the modal title to `Table Preview: ${tableName}`.
  - Calls `loadPreviewPage()`.
  - Sets `document.getElementById('preview-modal').style.display = 'flex'`.
- Add `async function loadPreviewPage()`:
  - Calls `api.getTablePreview(previewState.tableName, previewState.page, previewState.limit)`.
  - On error → renders the error in `#preview-error`.
  - On success → updates `previewState.columns/rows/totalPages`, hides error, calls `renderPreviewTable()`, and updates `#preview-page-indicator` to `Page ${page} of ${totalPages}`.
  - Disables `#preview-prev-page` when `page <= 1`; disables `#preview-next-page` when `page >= totalPages`.
- Add `function renderPreviewTable()`:
  - Builds `<table class="preview-table">` with header row: column names + a final `Actions` column.
  - For each row in `previewState.rows`:
    - `<tr data-rowid="{rowid}">`.
    - For each column, a `<td>` containing a `<span class="preview-cell" data-rowid="{rowid}" data-column="{col}">{value}</span>`. NULL values render as empty string but use a placeholder attribute `data-null="true"`.
    - Final `<td class="preview-row-actions">` with a delete button (`.preview-delete-row`) wired to `handleDeleteRow(rowid)`.
  - Replaces `#preview-table-container` content with this fresh table.
- Add `function handleCellClick(span: HTMLSpanElement)`:
  - Replaces the span with `<input class="preview-cell-input" value="...">`.
  - Focuses & selects all.
  - On `keydown`:
    - Enter → call `handleCellSave(input, span)`.
    - Escape → revert to original span (no save).
  - On `blur` → revert without saving (Escape-equivalent — keeps UX simple and predictable).
- Add `async function handleCellSave(input, span)`:
  - Gets `rowid` and `column` from data attrs.
  - Calls `api.updateRow(previewState.tableName, { rowid, updates: { [column]: input.value } })`.
  - On success → updates `span.textContent` to the new value; replaces input with span.
  - On failure → shows error in `#preview-error`, keeps input visible for retry.

### Step 13: Implement Add Row and Delete Row
- Add `async function handleAddRow()`:
  - Calls `api.insertRow(previewState.tableName, { data: {} })` (creates an empty row first; user fills cells inline).
  - On success → reload the **last** page so the new row is visible: `previewState.page = response.row_count_total_pages_after_insert` (compute from `response.row_count`); call `loadPreviewPage()`. Also call `loadDatabaseSchema()` to refresh the schema panel row count.
  - On failure → display error in `#preview-error`.
- Wire `#preview-add-row-button` click to `handleAddRow`.
- Add `async function handleDeleteRow(rowid: number)`:
  - `if (!confirm('Are you sure you want to delete this row?')) return;`
  - Calls `api.deleteRow(previewState.tableName, rowid)`.
  - On success → reload the current page (`loadPreviewPage()`) and `loadDatabaseSchema()`. If the current page becomes empty (e.g., last item on page N>1 deleted), decrement `previewState.page` and reload.
  - On failure → display error.
- Add **Previous** / **Next** click handlers that mutate `previewState.page` and call `loadPreviewPage()`.
- Wire the close button (`.close-preview-modal`) and modal-background click to hide `#preview-modal` and clear `previewState`.

### Step 14: Refresh schema panel after mutations
- Confirm `loadDatabaseSchema()` is called after every successful insert/delete (Step 13). It is already exposed at module scope.
- No call needed after a cell update — row count does not change.

### Step 15: Create the E2E test file
- IMPORTANT: Read `.claude/commands/test_e2e.md` and `.claude/commands/e2e/test_basic_query.md` first to understand the format.
- Create `.claude/commands/e2e/test_data_preview_inline_editing.md` with the standard sections (`# E2E Test: ...`, `User Story`, `Test Steps` with `**Verify**` keyword, `Success Criteria`).
- Test outline (minimal but complete coverage of acceptance criteria):
  1. Navigate to the app URL.
  2. Click the **Users Data** sample button (loads ~20 users).
  3. **Verify** the `users` table appears in **Available Tables** with the correct row count.
  4. Take a screenshot of the schema panel.
  5. Click the table name **users**.
  6. **Verify** the preview modal opens with column headers and rows.
  7. **Verify** "Page 1 of 1" indicator (since 20 rows < 50).
  8. Take a screenshot of the open preview.
  9. Click the first cell of the first row, type a new value, press **Enter**.
  10. **Verify** the cell now displays the new value.
  11. Reload the page and re-open the preview; **Verify** the change persisted.
  12. Click **Add Row**; **Verify** a new row appears, total rows is 21.
  13. **Verify** the schema panel now shows 21 rows (close modal first / inspect underlying tables list).
  14. Re-open preview; click the delete (×) button on the last row; confirm dialog.
  15. **Verify** total rows is back to 20 and the schema panel reflects this.
  16. Take a final screenshot.
- Output JSON format (status: passed|failed, screenshots array, error: null) per `.claude/commands/test_e2e.md`.

### Step 16: Run validation suite
- Execute every command in **Validation Commands** below, in order. Fix any failures before declaring done.

## Testing Strategy

### Unit Tests
Server-side (`app/server/tests/test_table_rows.py`):
- Pagination: page 1 returns 50 rows, page 2 returns remaining, total_pages computed correctly, page beyond total_pages returns empty rows array (not 404).
- Validation: invalid table name → 400; SQL-keyword as column → 400; missing table → 404.
- Update: happy-path persistence, unknown column rejected, non-existent rowid → 404, empty updates dict → 400.
- Insert: happy-path returns new rowid; empty data dict inserts NULL row; new row visible in subsequent preview.
- Delete: happy-path decrements row count; non-existent rowid → 404.
- Security: Ensure SQL injection attempts in `table_name`, column names, and the JSON body are blocked by `validate_identifier`. Reuse existing patterns in `tests/test_sql_injection.py`.

### Edge Cases
- Tables with NULL values — preview renders empty string; editing then saving an empty string should write empty string (not NULL); explicitly setting a value back to empty stays empty. (Document this trade-off; deeper NULL UX is out of scope.)
- Tables with mixed-type columns (TEXT containing numeric strings) — UPDATE preserves whatever the user types as the original column type per SQLite's type affinity; tests should confirm a string-typed column accepts numeric strings without error.
- Page size boundary: insert one row when `total_rows` is exactly `limit * N`; verify a new last page (N+1) appears with one row.
- Deleting the last row on page > 1 — UI auto-decrements `page` so the user doesn't see an empty page.
- Tables with a single column or zero data rows — preview still opens; "Add Row" works.
- Concurrent edit race (two browser tabs) — last write wins; out of scope to surface conflicts; document in Notes.
- Identifier with spaces (allowed by `validate_identifier`) — verify URL path encoding round-trips correctly.
- Very wide table (many columns) — modal scrolls horizontally (CSS `overflow: auto` on `.modal-content-wide`).

## Acceptance Criteria
1. Clicking a table name in **Available Tables** opens the preview modal showing the correct rows and column headers from that table.
2. Pagination works: with > 50 rows, clicking **Next** displays a different set of rows, and the **Page X of Y** indicator is accurate (Y = `ceil(total_rows / 50)`).
3. Clicking a cell makes it editable; pressing **Enter** saves the change; pressing **Escape** reverts the original value without saving.
4. Edited values persist across a full browser page refresh (validated by re-opening the modal after refresh).
5. **Add Row** inserts a visible new row in the preview that persists after refresh.
6. **Delete Row** prompts for confirmation; on confirm, the row is permanently removed from SQLite.
7. The schema panel's row count for the affected table updates after adding or deleting a row (no manual page refresh needed).
8. Server unit tests in `tests/test_table_rows.py` pass.
9. The E2E test in `.claude/commands/e2e/test_data_preview_inline_editing.md` passes.
10. All existing tests still pass (zero regressions).
11. SQL injection attempts via the new endpoints (table name, column name, body fields) are blocked at the server boundary with a 400 response.

## Validation Commands
Execute every command to validate the feature works correctly with zero regressions.

- `cd app/server && uv run pytest` — Run server tests (existing + new `test_table_rows.py`) to validate server behavior with zero regressions.
- `cd app/server && uv run pytest tests/test_sql_injection.py -v` — Re-run security-specific tests to confirm no security regressions in the new endpoints.
- `cd app/client && bun tsc --noEmit` — Type-check the client code.
- `cd app/client && bun run build` — Build the client to confirm zero build errors.
- Read `.claude/commands/test_e2e.md`, then read and execute `.claude/commands/e2e/test_data_preview_inline_editing.md` to validate the full UI flow works end-to-end with screenshots.

## Notes
- **No new Python or JS dependencies needed.** Pagination math uses `math.ceil`. SQLite's built-in `rowid` is used for stable row identity — no schema migration required even for tables created from CSV/JSON without an explicit `INTEGER PRIMARY KEY`.
- **Why `rowid` over a synthetic id column?** User-uploaded CSV/JSON tables don't have a guaranteed primary key. Adding one would require schema rewriting. SQLite always exposes a stable `rowid` (unless the table is `WITHOUT ROWID`, which `convert_csv_to_sqlite` / `convert_json_to_sqlite` do not produce).
- **DML safety:** the existing `execute_query_safely` blocks DDL (DROP/CREATE/ALTER/TRUNCATE) only when `allow_ddl=False`. UPDATE/INSERT/DELETE pass through, with values bound via `?` placeholders and identifiers validated/escaped via `identifier_params`. No call to `allow_ddl=True` is needed for the new endpoints.
- **Type coercion:** SQLite's dynamic typing means we can pass strings into `?` placeholders for INTEGER/REAL columns and SQLite will coerce per column affinity. We do not validate types client-side — keeping the UX permissive is consistent with how the existing query path handles types.
- **Security boundary:** every new endpoint validates `table_name` and every column name in user input via `validate_identifier`; only column names that match the table's actual schema are allowed in UPDATE/INSERT. Body values flow through `?` placeholders. This matches the existing app's security posture documented in `README.md` (lines 137-184).
- **Out of scope (future enhancements):** type-aware editors (date pickers, number inputs), multi-row selection/bulk delete, undo/redo, optimistic concurrency control, sorting/filtering inside the preview, NULL vs empty-string distinction in the UI, and column add/remove (DDL).
- **`adw_sdlc_iso` and `model_set heavy` flags** in the issue body are ADW workflow directives, not implementation requirements. They are handled by the ADW framework itself.
