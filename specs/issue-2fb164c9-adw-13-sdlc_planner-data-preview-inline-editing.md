# Feature: Data Preview with Inline Editing

## Metadata
issue_number: `2fb164c9`
adw_id: `13`
issue_json: `{"number":13,"title":"Data Preview with Inline Editing","body":"/feature\n\nadw_sdlc_iso\n\nmodel_set base\n\nClick a table name in the schema panel to open a paginated preview (50 rows). Click any cell to edit it in place. Add or delete rows with buttons. Changes save back to SQLite.\n\n**Scope:**\n- Server: `GET /api/table/{name}/preview?page=1&limit=50`, `PATCH /api/table/{name}/row` (update), `POST /api/table/{name}/row` (insert), `DELETE /api/table/{name}/row/{rowid}` (delete)\n- Client: Preview modal with editable cells, add/delete row buttons, pagination\n\n**Acceptance criteria:**\n1. Clicking a table name opens a preview showing correct data with column headers\n2. Pagination works: page 2 shows different rows; \"Page X of Y\" is accurate\n3. Clicking a cell makes it editable; Enter saves; Escape reverts without saving\n4. Edited values persist after page refresh\n5. \"Add Row\" inserts a visible new row that persists after refresh\n6. \"Delete Row\" asks for confirmation, then removes the row permanently\n7. Schema panel row count updates after adding or deleting rows\n"}`

## Feature Description

This feature adds a data preview and inline editing capability to the existing Natural Language SQL Interface. Currently users can upload CSV/JSON/JSONL files and query them via natural language, but there is no way to browse or directly edit the underlying table data. This feature allows users to click any table name in the schema panel to open a paginated preview modal (50 rows per page) showing the full table data. Within the modal, users can click any cell to edit it in place, add new rows, and delete existing rows. All changes persist immediately to the SQLite database.

## User Story

As a data analyst
I want to click a table name to preview its data and edit cells, rows, or delete rows directly
So that I can correct data issues and manage table contents without writing SQL queries

## Problem Statement

After uploading a file, users have no way to inspect the raw table data beyond running a natural language query. There is no mechanism to correct erroneous values, add missing rows, or remove incorrect records without re-uploading the file. This creates friction in iterative data-cleaning workflows.

## Solution Statement

Add four new REST endpoints to the FastAPI backend that support paginated preview, row update, row insert, and row delete. On the frontend, make each table name in the schema panel a clickable link that opens a modal with a paginated, editable data table. Cells enter edit mode on click; row mutations call the new API endpoints and refresh the schema panel row count.

## Relevant Files

Use these files to implement the feature:

- **`app/server/server.py`** — Main FastAPI app; add the four new route handlers here following the existing pattern (e.g., `DELETE /api/table/{table_name}`)
- **`app/server/core/data_models.py`** — Add new Pydantic request/response models for preview, update, insert, and delete operations
- **`app/server/core/sql_security.py`** — Use `validate_identifier()` and `escape_identifier()` for safe table/column name handling; use parameterized queries for values
- **`app/server/core/sql_processor.py`** — Reference for the existing pattern of direct SQLite operations; new table_editor module follows the same DB path convention
- **`app/server/tests/test_sql_injection.py`** — Reference for existing test patterns; add new tests in a parallel file
- **`app/client/src/main.ts`** — Add preview modal logic: click handlers on table names, modal rendering, cell editing, pagination, add/delete row buttons, schema refresh
- **`app/client/src/api/client.ts`** — Add four new API client methods: `getTablePreview`, `updateTableRow`, `insertTableRow`, `deleteTableRow`
- **`app/client/src/style.css`** — Add styles for the preview modal, editable cells, pagination controls, and row action buttons
- **`app/client/index.html`** — Add the preview modal HTML structure

Read `.claude/commands/test_e2e.md` and `.claude/commands/e2e/test_basic_query.md` to understand how to create an E2E test file.

### New Files

- **`app/server/core/table_editor.py`** — New core module with four functions: `get_table_preview`, `update_table_row`, `insert_table_row`, `delete_table_row`. Constructs DML queries programmatically (not via user input) using `escape_identifier` for identifiers and parameterized values for data — bypasses `validate_sql_query()` since queries are internally generated, not user-supplied.
- **`app/server/tests/test_table_editor.py`** — Unit tests for the new `table_editor` module
- **`.claude/commands/e2e/test_data_preview_inline_editing.md`** — E2E test file validating the full preview and editing workflow

## Implementation Plan

### Phase 1: Foundation

Add new Pydantic models to `data_models.py` and create the `table_editor.py` core module with safe SQLite DML operations. Write unit tests in `test_table_editor.py`. This phase must be complete before adding endpoints or UI.

### Phase 2: Core Implementation

Add four new endpoints in `server.py` that delegate to `table_editor.py`. Add four new API client methods in `api/client.ts`. Build the preview modal HTML in `index.html` and implement the full modal logic (rendering, cell editing, pagination, add/delete) in `main.ts`. Add CSS for the modal and interactive elements in `style.css`.

### Phase 3: Integration

Wire the schema panel table name click to open the preview modal. After any mutation (add/delete row), refresh the schema panel to reflect updated row counts. Create the E2E test file and validate the complete workflow end-to-end.

## Step by Step Tasks

### Step 1: Add new Pydantic models to `data_models.py`

- Add `TablePreviewResponse` with fields: `columns: list[str]`, `rows: list[list]`, `page: int`, `total_pages: int`, `total_rows: int`, `page_size: int`, `error: str | None`
- Add `RowUpdateRequest` with fields: `rowid: int`, `values: dict[str, Any]`
- Add `RowInsertRequest` with fields: `values: dict[str, Any]`
- Add `RowMutationResponse` with fields: `success: bool`, `row_count: int | None`, `error: str | None`

### Step 2: Create `app/server/core/table_editor.py`

- Import `sqlite3`, `math`, `logging`; import `validate_identifier`, `escape_identifier`, `SQLSecurityError` from `sql_security`
- Define `DB_PATH = "db/database.db"` (same as `sql_processor.py`)
- Implement `get_table_preview(table_name: str, page: int, limit: int) -> dict`:
  - Validate `table_name` with `validate_identifier()`
  - Validate `page >= 1` and `1 <= limit <= 200`
  - Query total row count: `SELECT COUNT(*) FROM [table_name]`
  - Calculate `total_pages = ceil(total_rows / limit)`, `offset = (page - 1) * limit`
  - Query data: `SELECT rowid, * FROM [table_name] LIMIT ? OFFSET ?`
  - Return dict with `columns` (including "rowid"), `rows` (list of lists), `page`, `total_pages`, `total_rows`, `page_size`
- Implement `update_table_row(table_name: str, rowid: int, values: dict) -> dict`:
  - Validate `table_name` with `validate_identifier()`
  - Validate `rowid` is a positive integer
  - Validate each column key with `validate_identifier()`
  - Build `UPDATE [table] SET [col1]=?, [col2]=? WHERE rowid=?` using `escape_identifier` for column names, parameterized `?` for values and rowid
  - Execute and return `{"success": True, "row_count": None}`
- Implement `insert_table_row(table_name: str, values: dict) -> dict`:
  - Validate `table_name` and all column keys
  - Build `INSERT INTO [table] ([col1], [col2]) VALUES (?, ?)` with escaped identifiers and parameterized values
  - Query updated row count after insert
  - Return `{"success": True, "row_count": new_total}`
- Implement `delete_table_row(table_name: str, rowid: int) -> dict`:
  - Validate `table_name`, validate `rowid` is a positive integer
  - Execute `DELETE FROM [table] WHERE rowid=?` with parameterized rowid
  - Query updated row count after delete
  - Return `{"success": True, "row_count": new_total}`
- All functions: wrap in try/except, return `{"success": False, "error": str(e)}` on failure

### Step 3: Write unit tests in `app/server/tests/test_table_editor.py`

- Create an in-memory or temp-file SQLite database fixture with a test table containing 5 rows
- Monkey-patch `DB_PATH` in `table_editor` module to point to the temp DB
- `test_get_table_preview_first_page` — assert columns, rows count, total_rows, total_pages
- `test_get_table_preview_second_page` — verify page 2 returns different rows
- `test_get_table_preview_invalid_table_name` — assert error returned for invalid name
- `test_update_table_row` — update a cell value, re-query, assert new value
- `test_update_table_row_invalid_column` — assert error for SQL keyword as column name
- `test_insert_table_row` — insert a row, assert row_count increased by 1
- `test_delete_table_row` — delete a row, assert row_count decreased by 1
- `test_delete_table_row_invalid_rowid` — assert error for non-integer rowid

### Step 4: Add four new endpoints to `app/server/server.py`

- `GET /api/table/{name}/preview` with query params `page: int = 1, limit: int = 50`:
  - Call `table_editor.get_table_preview(name, page, limit)`
  - Return `TablePreviewResponse` (or 400 on error)
- `PATCH /api/table/{name}/row` accepting `RowUpdateRequest`:
  - Call `table_editor.update_table_row(name, request.rowid, request.values)`
  - Return `RowMutationResponse`
- `POST /api/table/{name}/row` accepting `RowInsertRequest`:
  - Call `table_editor.insert_table_row(name, request.values)`
  - Return `RowMutationResponse`
- `DELETE /api/table/{name}/row/{rowid}`:
  - Validate `rowid` is a positive integer; return 400 if not
  - Call `table_editor.delete_table_row(name, rowid)`
  - Return `RowMutationResponse`

### Step 5: Add new API client methods to `app/client/src/api/client.ts`

- `getTablePreview(tableName: string, page: number, limit: number = 50)` — GET `/api/table/{tableName}/preview?page={page}&limit={limit}`
- `updateTableRow(tableName: string, rowid: number, values: Record<string, unknown>)` — PATCH `/api/table/{tableName}/row`
- `insertTableRow(tableName: string, values: Record<string, unknown>)` — POST `/api/table/{tableName}/row`
- `deleteTableRow(tableName: string, rowid: number)` — DELETE `/api/table/{tableName}/row/{rowid}`
- Add corresponding TypeScript types: `TablePreviewResponse`, `RowMutationResponse`

### Step 6: Add preview modal HTML to `app/client/index.html`

- Add a `<div id="preview-modal" class="modal hidden">` after the existing upload modal
- Inside: modal overlay backdrop, modal content container with:
  - Header: `<h3 id="preview-modal-title">`, close (×) button
  - Toolbar: `<button id="add-row-btn">Add Row</button>`, `<span id="preview-status"></span>`
  - Scrollable table container: `<div id="preview-table-container"><table id="preview-table"></table></div>`
  - Pagination footer: `<button id="prev-page-btn">`, `<span id="page-info">Page 1 of N</span>`, `<button id="next-page-btn">`

### Step 7: Add preview modal CSS to `app/client/src/style.css`

- Style the preview modal overlay (fixed fullscreen, semi-transparent backdrop) consistent with the existing upload modal pattern
- Style the preview table (full width, compact rows, sticky header)
- Style editable cells: `.cell-editing input` with border highlight
- Style the Add Row button consistent with existing button styles
- Style Delete Row button per row (small, red-tinted, in a dedicated action column)
- Style pagination controls (flex row, centered)
- Style `.cell-editing` state (blue border, subtle background)

### Step 8: Implement preview modal logic in `app/client/src/main.ts`

- **State**: add module-level variables `previewTableName`, `previewCurrentPage`, `previewTotalPages`
- **`openPreviewModal(tableName)`**:
  - Set `previewTableName = tableName`, `previewCurrentPage = 1`
  - Show modal, set title to table name
  - Call `loadPreviewPage(1)`
- **`closePreviewModal()`**: hide modal, reset state
- **`loadPreviewPage(page)`**:
  - Call `apiClient.getTablePreview(previewTableName, page)`
  - Render table: header row with column names (skip rendering "rowid" as a visible column but track it in a data attribute per row), data rows
  - Each data cell: `<td data-col="colname">value</td>`, clicking calls `startCellEdit(td, rowid, colname)`
  - Each data row: append a `<td><button class="delete-row-btn">Delete</button></td>` action cell
  - Update `#page-info` to "Page X of Y"
  - Enable/disable Prev/Next buttons based on current page vs total pages
- **`startCellEdit(td, rowid, colname)`**:
  - Replace cell content with `<input type="text" value="currentValue">`
  - Focus the input
  - On Enter key: call `saveCellEdit(td, rowid, colname, input.value)`
  - On Escape key: restore original cell text, remove input
- **`saveCellEdit(td, rowid, colname, newValue)`**:
  - Call `apiClient.updateTableRow(previewTableName, rowid, {[colname]: newValue})`
  - On success: update `td.textContent = newValue`
  - On error: restore original value, show error in `#preview-status`
- **`addRow()`** (bound to `#add-row-btn`):
  - Call `apiClient.insertTableRow(previewTableName, {})` with empty values (SQLite will use NULLs)
  - On success: reload current page; refresh schema via `loadSchema()`
- **`deleteRow(rowid)`** (bound to delete buttons):
  - `window.confirm("Delete this row permanently?")` — return if cancelled
  - Call `apiClient.deleteTableRow(previewTableName, rowid)`
  - On success: reload current page; refresh schema via `loadSchema()`
- **Schema panel click handler**:
  - In `displayTables()`, wrap each table name `<span>` in a `<button class="table-name-btn">` or make it clickable; add `onclick="openPreviewModal('tableName')"`
- **Pagination**:
  - `#prev-page-btn` click: `loadPreviewPage(previewCurrentPage - 1)`
  - `#next-page-btn` click: `loadPreviewPage(previewCurrentPage + 1)`

### Step 9: Create the E2E test file

- Read `.claude/commands/test_e2e.md` and `.claude/commands/e2e/test_basic_query.md` for format and conventions
- Create `.claude/commands/e2e/test_data_preview_inline_editing.md` with:
  - User story matching the feature
  - Test steps:
    1. Navigate to the app URL
    2. Take screenshot of initial state
    3. Verify schema panel shows at least one table (upload sample data if none present: drag users.json from `/sample-data/`)
    4. Click a table name in the schema panel — verify preview modal opens
    5. Take screenshot of the open preview modal
    6. Verify column headers and data rows are visible
    7. Verify "Page 1 of Y" is displayed
    8. If total_pages > 1: click Next — verify "Page 2 of Y" is shown and different data appears
    9. Take screenshot of pagination state
    10. Click a data cell — verify an input appears
    11. Type a new value — press Enter
    12. Take screenshot of the edited cell
    13. Close and reopen the preview modal — verify the new value persists
    14. Click "Add Row" — verify a new row appears in the table; verify schema panel row count increased
    15. Take screenshot showing new row
    16. Click "Delete Row" on any row — click OK in confirmation dialog — verify row is removed; verify schema panel row count decreased
    17. Take screenshot of final state
  - Success criteria matching all 7 acceptance criteria
  - Screenshot list (at least 5)

### Step 10: Run validation commands

- Run all validation commands listed in the Validation Commands section

## Testing Strategy

### Unit Tests

- **`test_table_editor.py`**: Test each of the four functions against a real temporary SQLite DB (no mocks for the DB layer). Cover happy path and error cases including invalid table names, invalid column names (SQL keywords), non-existent rowids, and out-of-range page numbers.
- The existing `test_sql_injection.py` patterns should be referenced to ensure the new `table_editor.py` module is equally resistant to injection via table name and column name parameters.

### Edge Cases

- Page number beyond total_pages — return empty rows, total_pages is still accurate
- `limit=0` or `limit > 200` — return 400 validation error
- Update/delete a rowid that no longer exists — return success with 0 rows affected (SQLite behavior); frontend reloads page
- Insert row into a table with NOT NULL constraints — return error from SQLite propagated to client
- Table name containing special characters passed via URL — validated by `validate_identifier()`, returns 400
- Column name that is a SQL keyword (e.g., "select") — `validate_identifier()` rejects it, returns error
- Very long string value in a cell — SQLite TEXT type stores it; no truncation
- Editing "rowid" column — rowid column must not be rendered as an editable cell (it is the internal record locator)

## Acceptance Criteria

1. Clicking a table name in the schema panel opens a preview modal displaying correct data with column headers and data rows
2. Pagination works: navigating to page 2 shows different rows; "Page X of Y" text is accurate; Prev/Next buttons are disabled at boundaries
3. Clicking a cell replaces its content with an input; pressing Enter sends a PATCH request and updates the cell display; pressing Escape restores the original value without an API call
4. An edited cell value persists after closing and reopening the preview modal (confirmed by re-fetching from the server)
5. Clicking "Add Row" inserts a new row visible in the preview table and the row count in the schema panel increments
6. Clicking "Delete Row" shows a browser confirmation dialog; confirming removes the row permanently and decrements the schema panel row count; cancelling leaves the row intact
7. Schema panel row count is accurate after any add or delete operation (reloaded via `loadSchema()`)

## Validation Commands

- Read `.claude/commands/test_e2e.md`, then read and execute `.claude/commands/e2e/test_data_preview_inline_editing.md` to validate the full preview and editing workflow
- `cd app/server && uv run pytest` — Run server tests to validate the feature works with zero regressions
- `cd app/client && bun tsc --noEmit` — Run TypeScript type checking to validate the feature works with zero regressions
- `cd app/client && bun run build` — Run frontend build to validate the feature works with zero regressions

## Notes

- **rowid vs explicit primary key**: SQLite's built-in `rowid` pseudo-column is the stable record identifier for this feature. The preview query always fetches `SELECT rowid, * FROM [table]` so the rowid is available per row without modifying existing table schemas.
- **DML security model**: `table_editor.py` constructs SQL programmatically using `escape_identifier()` for all column and table names and `?` parameterized placeholders for all values. It intentionally does NOT call `validate_sql_query()` because that function is designed to block user-supplied SQL strings, not internally-constructed DML. The security is achieved at the identifier and value level, not the SQL string level.
- **Empty row insert**: `INSERT INTO [table] DEFAULT VALUES` is used when `values` dict is empty, so SQLite fills all columns with their default (typically NULL). This is valid SQLite syntax.
- **No new dependencies required**: All functionality uses the Python standard library (`sqlite3`, `math`) and existing FastAPI/Pydantic. No `uv add` needed.
- **`loadSchema()` refresh**: The existing `displayTables()` / schema loading flow in `main.ts` is reused after mutations to update row counts in the schema panel without page reload.
- **Modal pattern**: Follow the existing upload modal pattern in `index.html` and `style.css` for visual consistency (same backdrop, close button style, and z-index layering).
