# Feature: Data Preview with Inline Editing

## Metadata
issue_number: `3a18505f`
adw_id: `42`
issue_json: `{"number":42,"title":"3. Data Preview with Inline Editing","body":"/feature\n\nadw_sdlc_iso\n\nmodel_set heavy\n\nClick a table name in the schema panel to open a paginated preview (50 rows). Click any cell to edit it in place. Add or delete rows with buttons. Changes save back to SQLite.\n\n**Scope:**\n- Server: `GET /api/table/{name}/preview?page=1&limit=50`, `PATCH /api/table/{name}/row` (update), `POST /api/table/{name}/row` (insert), `DELETE /api/table/{name}/row/{rowid}` (delete)\n- Client: Preview modal with editable cells, add/delete row buttons, pagination\n\n**Acceptance criteria:**\n1. Clicking a table name opens a preview showing correct data with column headers\n2. Pagination works: page 2 shows different rows; \"Page X of Y\" is accurate\n3. Clicking a cell makes it editable; Enter saves; Escape reverts without saving\n4. Edited values persist after page refresh\n5. \"Add Row\" inserts a visible new row that persists after refresh\n6. \"Delete Row\" asks for confirmation, then removes the row permanently\n7. Schema panel row count updates after adding or deleting rows\n"}`

## Feature Description
Add a data preview modal that lets users inspect and edit the contents of any SQLite table directly from the schema panel. Clicking a table name opens a paginated preview (50 rows per page) with column headers. Cells are click-to-edit (Enter to save, Escape to revert). Users can insert and delete rows via dedicated buttons; all changes are persisted to SQLite immediately. The schema panel row counts re-sync after any insert or delete so the UI is always accurate.

This brings simple spreadsheet-style data editing into the app without requiring users to leave the natural-language workflow, write SQL, or open a separate DB client.

## User Story
As a user of the Natural Language SQL Interface
I want to click a table name to preview, edit, add, and delete its rows in place
So that I can quickly correct data and inspect contents without writing SQL or using an external tool

## Problem Statement
Today the schema panel only shows table metadata (name, row count, columns). Users who want to inspect raw rows must run a `SELECT *` natural-language query, and editing/adding/deleting rows is not possible at all from the UI — they would need to drop and re-upload the file or open the SQLite DB by hand. This breaks the workflow for anyone who needs to make small corrections or quickly verify what actually lives in a table.

## Solution Statement
Add four CRUD endpoints scoped to a single table on the server (preview with pagination, update row, insert row, delete row), each going through `core/sql_security.py` for identifier validation and parameterized values. On the client, make the table name in the schema panel a clickable element that opens a new preview modal with:
- A paginated table view (50 rows per page, prev/next buttons, "Page X of Y" indicator)
- Click-to-edit cells using `contenteditable` (Enter commits, Escape reverts)
- "Add Row" button that inserts a blank row via the insert endpoint
- "Delete Row" button per row with a confirm dialog
- A refresh of the schema panel row counts after every mutation

All mutations use SQLite's built-in `rowid` as the stable identifier, so this works for every table created by file upload without requiring an explicit primary key.

## Relevant Files
Use these files to implement the feature:

- `README.md` — Project overview, commands, and conventions. Read first to understand the architecture and start scripts.
- `app/server/server.py` — FastAPI app; this is where the four new endpoints (`GET /api/table/{name}/preview`, `PATCH /api/table/{name}/row`, `POST /api/table/{name}/row`, `DELETE /api/table/{name}/row/{rowid}`) will be added alongside the existing `DELETE /api/table/{name}` handler.
- `app/server/core/data_models.py` — Pydantic request/response models; new models for preview response, row update request, row insert request/response, and row delete response will be added here.
- `app/server/core/sql_security.py` — Identifier validation and `execute_query_safely`. The new endpoints must use these helpers for table/column name validation and identifier escaping. Note that `validate_sql_query` blocks `DELETE FROM` / `UPDATE ... SET` / `INSERT ... SELECT`, so the new write endpoints must call `cursor.execute` directly with parameterized values (not route through `validate_sql_query`).
- `app/server/core/sql_processor.py` — Reference for how existing code opens connections (`sqlite3.connect("db/database.db")`, `row_factory = sqlite3.Row`) and how `PRAGMA table_info` is used to discover columns.
- `app/server/core/file_processor.py` — Reference for SQLite write patterns and column-type discovery.
- `app/server/tests/test_sql_injection.py` — Existing test patterns (pytest fixtures, tempfile DB, SQL injection assertions). Mirror this style for new endpoint tests.
- `app/client/index.html` — Add a hidden preview-modal element with placeholder containers for the title, body, pagination controls, and add-row button.
- `app/client/src/main.ts` — Where the table-name click handler, modal open/close, cell editing, pagination, add/delete row handlers, and schema-panel refresh will live. Also where the existing tables list is rendered (so the table name needs to become a clickable element).
- `app/client/src/api/client.ts` — Add four new API methods (`getTablePreview`, `updateTableRow`, `insertTableRow`, `deleteTableRow`).
- `app/client/src/types.d.ts` — Add TypeScript types mirroring the new Pydantic models.
- `app/client/src/style.css` — Add styles for the preview modal, the editable cell hover/focus state, the pagination controls, the add-row button, and the per-row delete control. Reuse the existing `.modal` / `.modal-content` / `.modal-header` / `.modal-body` classes already defined.
- `.claude/commands/test_e2e.md` — Read to understand how E2E tests are executed by Playwright; reference for the new E2E test's expected format.
- `.claude/commands/e2e/test_basic_query.md` — Read as a template for what an E2E test file looks like (User Story, Test Steps, Success Criteria, screenshot counts).

### New Files
- `app/server/tests/test_table_crud.py` — Pytest module covering the four new endpoints (preview pagination, row update, row insert, row delete) including identifier-injection rejection and not-found cases.
- `.claude/commands/e2e/test_data_preview_inline_editing.md` — Playwright E2E test that walks through opening the modal, paginating, editing a cell, adding a row, deleting a row, and verifying schema-panel row count updates and persistence after reload.

## Implementation Plan

### Phase 1: Foundation
1. Define Pydantic models in `core/data_models.py` for the new request/response shapes.
2. Add four new endpoints in `server.py` that validate the table name with `validate_identifier`, confirm existence with `check_table_exists`, discover columns with `PRAGMA table_info`, and execute parameterized SQL using `sqlite3.Cursor.execute` directly (so we keep the new write operations off the `validate_sql_query` denylist while still being safe).
3. Add unit tests in `app/server/tests/test_table_crud.py` covering happy paths, pagination math, identifier-injection rejection, missing-table 404s, missing-rowid 404s, and that values round-trip correctly.

### Phase 2: Core Implementation
4. Extend `api/client.ts` with the four new methods and add matching types in `types.d.ts`.
5. Add the preview modal markup to `index.html` (hidden by default) and the matching styles in `style.css`.
6. In `main.ts`, make the table name clickable, wire the modal open/close, render the paginated grid with editable cells, and wire add/delete row buttons. Refresh `loadDatabaseSchema()` after every successful mutation so the schema-panel row count stays in sync.

### Phase 3: Integration
7. Verify the existing flows (upload, query, export, delete table) are unaffected by the new table-name click handler — clicking the existing `×` button must still remove the table without triggering the preview.
8. Create the E2E test file and run it end-to-end against the running app.
9. Run all validation commands (server tests, frontend type-check, frontend build, E2E test) and fix anything that surfaces.

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

### Step 1: Add Pydantic models
- In `app/server/core/data_models.py` add the following models:
  - `TablePreviewResponse`: `table_name: str`, `columns: List[str]`, `column_types: Dict[str, str]`, `rows: List[Dict[str, Any]]` (each row includes a `rowid` key), `total_rows: int`, `page: int`, `limit: int`, `total_pages: int`, `error: Optional[str] = None`.
  - `RowUpdateRequest`: `rowid: int`, `column: str`, `value: Optional[Any] = None`.
  - `RowMutationResponse`: `success: bool`, `rowid: int`, `row_count: int`, `error: Optional[str] = None` — used as the response for update, insert, and delete.
  - `RowInsertRequest`: `values: Dict[str, Any] = Field(default_factory=dict)` — empty dict means insert an all-NULL row.
- Do not add any decorators beyond the standard `BaseModel`/`Field` usage already present in the file.

### Step 2: Add `GET /api/table/{table_name}/preview` endpoint
- Add to `app/server/server.py` after the existing `DELETE /api/table/{table_name}` handler.
- Accept query params `page: int = 1` and `limit: int = 50`. Clamp `page >= 1` and `1 <= limit <= 200`.
- Validate `table_name` with `validate_identifier`; on failure raise `HTTPException(400, ...)`.
- Open `sqlite3.connect("db/database.db")`, set `row_factory = sqlite3.Row`.
- Use `check_table_exists`; if false, `HTTPException(404, ...)`.
- Get columns via `execute_query_safely(conn, "PRAGMA table_info({table})", identifier_params={"table": table_name})`.
- Get total row count via `execute_query_safely(conn, "SELECT COUNT(*) FROM {table}", identifier_params={"table": table_name})`.
- Compute `total_pages = max(1, ceil(total_rows / limit))`, `offset = (page - 1) * limit`.
- Fetch rows with `execute_query_safely(conn, "SELECT rowid AS rowid, * FROM {table} LIMIT ? OFFSET ?", params=(limit, offset), identifier_params={"table": table_name})`. Convert each `sqlite3.Row` to `dict`.
- Return `TablePreviewResponse(...)`. On any exception, log the traceback and return a response with `error=str(e)` and empty rows (mirroring existing endpoint error handling style).

### Step 3: Add `PATCH /api/table/{table_name}/row` endpoint
- Validate `table_name` and the request body's `column` field with `validate_identifier` (`column` type).
- Verify the column exists by running `PRAGMA table_info` and checking the column is present; if not, return 400.
- Build the SQL: use `execute_query_safely(conn, "UPDATE {table} SET {col} = ? WHERE rowid = ?", params=(value, rowid), identifier_params={"table": table_name, "col": column}, allow_ddl=False)`.
  - Important: `validate_sql_query` is **not** called here — `execute_query_safely` only checks for DDL keywords at the start of the statement, and `UPDATE` is not DDL, so this path is safe.
- `conn.commit()`. If `cursor.rowcount == 0`, raise `HTTPException(404, "Row not found")`.
- Re-query the row count for the response.
- Return `RowMutationResponse(success=True, rowid=rowid, row_count=row_count)`.

### Step 4: Add `POST /api/table/{table_name}/row` endpoint
- Validate `table_name`. Fetch column list with `PRAGMA table_info`.
- For every column key supplied in `RowInsertRequest.values`, validate it with `validate_identifier` and confirm it exists in the table.
- If `values` is empty, execute `INSERT INTO {table} DEFAULT VALUES` via `execute_query_safely` (no `params`, no DDL).
- Otherwise, build a SQL statement of the form `INSERT INTO {table} ({col1}, {col2}, ...) VALUES (?, ?, ...)`. Pre-validate and escape each column with `escape_identifier`, build the column list and matching parameter tuple, and run via `cursor.execute` directly (because `execute_query_safely`'s `{identifier}` substitution only handles a fixed set of named placeholders, and we have a variable column list).
- `conn.commit()`. The new rowid is `cursor.lastrowid`.
- Return `RowMutationResponse(success=True, rowid=cursor.lastrowid, row_count=<refreshed count>)`.

### Step 5: Add `DELETE /api/table/{table_name}/row/{rowid}` endpoint
- Validate `table_name`. Use `check_table_exists`.
- Execute `execute_query_safely(conn, "DELETE FROM {table} WHERE rowid = ?", params=(rowid,), identifier_params={"table": table_name})`.
  - As with UPDATE, this skips `validate_sql_query` which would otherwise block `DELETE FROM`.
- `conn.commit()`. If `cursor.rowcount == 0`, raise `HTTPException(404, "Row not found")`.
- Return `RowMutationResponse(success=True, rowid=rowid, row_count=<refreshed count>)`.

### Step 6: Add server unit tests
- Create `app/server/tests/test_table_crud.py` mirroring the structure of `tests/test_sql_injection.py`:
  - A `tmp_path`/`tempfile`-based fixture that creates a `db/database.db`, populates a `users` table with 75 rows so pagination is meaningful, and patches the working directory so the endpoints find the DB.
  - Use FastAPI's `TestClient` (`from fastapi.testclient import TestClient`) against `server.app`.
  - Tests:
    - `test_preview_first_page_returns_50_rows`
    - `test_preview_pagination_math_and_total_pages`
    - `test_preview_rejects_bad_identifier`
    - `test_preview_404_on_missing_table`
    - `test_update_row_persists_value`
    - `test_update_row_404_when_rowid_missing`
    - `test_update_row_rejects_unknown_column`
    - `test_insert_row_empty_creates_null_row` (verifies `rowid` returned and total count increments)
    - `test_insert_row_with_values_persists`
    - `test_delete_row_removes_row_and_returns_new_count`
    - `test_delete_row_404_when_rowid_missing`
    - `test_identifier_injection_blocked_on_all_endpoints` (try `users; DROP TABLE users` as the table name)

### Step 7: Add types and API client methods
- In `app/client/src/types.d.ts` add interfaces matching the new Pydantic models (`TablePreviewResponse`, `RowUpdateRequest`, `RowInsertRequest`, `RowMutationResponse`).
- In `app/client/src/api/client.ts` add:
  - `async getTablePreview(tableName: string, page: number, limit: number): Promise<TablePreviewResponse>` — `GET /table/${tableName}/preview?page=${page}&limit=${limit}`.
  - `async updateTableRow(tableName: string, body: RowUpdateRequest): Promise<RowMutationResponse>` — `PATCH /table/${tableName}/row`.
  - `async insertTableRow(tableName: string, body: RowInsertRequest): Promise<RowMutationResponse>` — `POST /table/${tableName}/row`.
  - `async deleteTableRow(tableName: string, rowid: number): Promise<RowMutationResponse>` — `DELETE /table/${tableName}/row/${rowid}`.

### Step 8: Add preview modal markup and styles
- In `app/client/index.html`, add a second hidden modal sibling to the existing `#upload-modal`:
  ```html
  <div id="preview-modal" class="modal" style="display: none;">
    <div class="modal-content preview-modal-content">
      <div class="modal-header">
        <h2 id="preview-modal-title">Preview</h2>
        <button class="close-preview-modal">&times;</button>
      </div>
      <div class="modal-body">
        <div id="preview-toolbar" class="preview-toolbar"></div>
        <div id="preview-table-container" class="preview-table-container"></div>
        <div id="preview-pagination" class="preview-pagination"></div>
      </div>
    </div>
  </div>
  ```
- In `app/client/src/style.css` add:
  - `.preview-modal-content { max-width: 1100px; width: 95%; max-height: 90vh; }`
  - `.preview-table-container { overflow: auto; max-height: 60vh; }`
  - `.preview-table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }` plus matching `th`/`td` rules consistent with `.results-table`.
  - `.preview-cell[contenteditable="true"]:hover { background: rgba(102, 126, 234, 0.08); cursor: text; }`
  - `.preview-cell:focus { outline: 2px solid var(--primary-color); background: white; }`
  - `.preview-pagination` flex row with `gap: 0.5rem` and centered alignment.
  - `.add-row-button` styled like `.secondary-button` but smaller.
  - `.delete-row-button` styled like `.remove-table-button` but inline-sized for table rows.
  - `.table-name.clickable` with `cursor: pointer; text-decoration: underline; text-decoration-style: dotted;` and a hover color matching `--primary-color`.

### Step 9: Make table names clickable and wire the modal
- In `app/client/src/main.ts`:
  - Where `displayTables` builds each `.table-name` element, add the `clickable` class and attach an `onclick` handler that calls `openTablePreview(table.name)`. Use `event.stopPropagation()` only if needed to keep the existing `×` remove-button click independent (the buttons are already separate children, but verify).
  - Add a new `initializePreviewModal()` called from `DOMContentLoaded` that wires the close button and background-click dismissal (mirroring `initializeModal`).
  - Add module-level state for the open preview: `let currentPreviewTable: string | null = null;` and `let currentPreviewPage = 1;`.
  - Implement `async function openTablePreview(tableName: string)` — sets state, shows the modal, calls `renderPreview()`.
  - Implement `async function renderPreview()` that:
    1. Calls `api.getTablePreview(currentPreviewTable!, currentPreviewPage, 50)`.
    2. Sets the modal title to `Preview: ${tableName}`.
    3. Renders a toolbar with an `Add Row` button.
    4. Renders the rows table: first column is a delete `×` button per row, then one `<td>` per column with `contenteditable="true"`, `data-rowid`, `data-column` attributes, and the value as text content (use empty string for `null`).
    5. Renders pagination with `Prev`, `Page X of Y`, `Next` controls. Disable `Prev` on page 1 and `Next` on the last page.

### Step 10: Wire cell editing
- For each editable `<td>`:
  - On `focus`, capture the original value into a `data-original` attribute.
  - On `keydown`:
    - `Enter`: prevent default newline, call `commitCellEdit(td)`, then `td.blur()`.
    - `Escape`: restore `td.textContent = td.dataset.original ?? ""`, then `td.blur()` without calling the API.
  - On `blur` (without explicit Enter), do nothing (keep behavior simple: only Enter commits, matching the spec).
- `commitCellEdit(td)`:
  - If `td.textContent === td.dataset.original`, no-op.
  - Otherwise call `api.updateTableRow(currentPreviewTable!, { rowid: Number(td.dataset.rowid), column: td.dataset.column!, value: td.textContent ?? "" })`.
  - On error, restore the original value and call `displayError`.
  - On success, update `data-original` to the new value and re-call `loadDatabaseSchema()` (row count itself doesn't change on update, but this keeps the contract simple and cheap).

### Step 11: Wire Add Row
- The toolbar's `Add Row` button click handler:
  - Calls `api.insertTableRow(currentPreviewTable!, { values: {} })`.
  - On success, jumps to the **last** page (`currentPreviewPage = Math.ceil(response.row_count / 50)`) so the new row is visible, re-renders the preview, and calls `loadDatabaseSchema()` so the schema panel row count updates.
  - On error, call `displayError`.

### Step 12: Wire Delete Row
- Each row's delete `×` button handler:
  - Calls `confirm('Delete this row? This cannot be undone.')`. If the user cancels, return.
  - Calls `api.deleteTableRow(currentPreviewTable!, rowid)`.
  - On success: if the current page is now empty (`response.row_count <= (currentPreviewPage - 1) * 50` and `currentPreviewPage > 1`), decrement `currentPreviewPage`. Re-render the preview and call `loadDatabaseSchema()`.
  - On error, call `displayError`.

### Step 13: Create the E2E test file
- Create `.claude/commands/e2e/test_data_preview_inline_editing.md`. Model the structure after `test_basic_query.md` and `test_export_functionality.md`. Test Steps should be approximately:
  1. Navigate to the `Application URL`; take a screenshot of the initial state.
  2. Click the "Users Data" sample button in the upload modal so a `users` table exists with 20 rows.
  3. **Verify** the `users` row appears in Available Tables; capture its row count (should be 20).
  4. Click the `users` table name in the schema panel.
  5. **Verify** the preview modal opens with the title `Preview: users`, a table of rows, column headers, and a `Page 1 of 1` (or similar) indicator. Take a screenshot.
  6. Click the first editable cell in the first row; clear it; type `Edited Value`; press Enter.
  7. **Verify** the cell text becomes `Edited Value`. Take a screenshot.
  8. Click `Add Row`; **verify** a new (mostly empty) row appears and the schema-panel row count is now 21. Take a screenshot.
  9. Click the delete `×` on the newly added row; confirm the dialog; **verify** the row disappears and the schema-panel row count returns to 20. Take a screenshot.
  10. Reload the page; re-open the preview; **verify** the edited cell still shows `Edited Value` (proves persistence).
  11. Close the modal.
- Success Criteria covers all 7 acceptance criteria from the issue plus screenshot count (5).

### Step 14: Run validation
- Execute every command in the **Validation Commands** section below. If anything fails, fix it and re-run.

## Testing Strategy

### Unit Tests
- `app/server/tests/test_table_crud.py` covers all four endpoints with happy paths, pagination math, identifier-injection rejection, 404s, and round-trip persistence (see Step 6 for the full list of test cases).
- Existing tests in `tests/test_sql_injection.py` and `tests/test_export_utils.py` must continue to pass — the new endpoints share `sql_security` helpers, so any regression there would be caught.

### Edge Cases
- Empty table preview (`total_rows = 0` → `total_pages = 1`, `rows = []`).
- Last page partially full (e.g., 75 rows, limit 50 → page 2 has 25 rows).
- `page` out of bounds (e.g., page 99 of a 1-page table → returns empty rows, not 404).
- Cell value containing characters that look like SQL (`'; DROP TABLE users;--`) — parameterized values must persist verbatim.
- Editing a cell to an empty string — should store `''` (not NULL); deliberate NULL handling is out of scope for v1 and noted in **Notes**.
- Inserting an empty row into a table with `NOT NULL` columns — server returns the SQLite error in the response's `error` field rather than 500.
- Identifier injection on every endpoint (`users; DROP TABLE users` as `table_name`, `id; DROP` as `column`) — must be rejected with 400.
- Deleting the last row on a page > 1 — UI jumps back one page.
- Adding a row jumps the UI to the page containing the new row.
- The existing `×` (remove table) button must still work and must not trigger the preview modal.

## Acceptance Criteria
Mirrors the issue's seven acceptance criteria, verified by the E2E test:

1. Clicking a table name opens a preview showing correct data with column headers.
2. Pagination works: page 2 shows different rows; "Page X of Y" is accurate.
3. Clicking a cell makes it editable; Enter saves; Escape reverts without saving.
4. Edited values persist after page refresh.
5. "Add Row" inserts a visible new row that persists after refresh.
6. "Delete Row" asks for confirmation, then removes the row permanently.
7. Schema panel row count updates after adding or deleting rows.

Additional non-functional criteria:
- All four new endpoints validate identifiers and reject injection attempts (covered by unit tests).
- Server tests, frontend type-check, and frontend build all complete without errors.

## Validation Commands
Execute every command to validate the feature works correctly with zero regressions.

- `cd app/server && uv run pytest` — Runs the new `test_table_crud.py` plus the existing SQL-injection and export test suites with zero regressions.
- `cd app/client && bun tsc --noEmit` — Type-check the client so the new API methods, types, and DOM code compile cleanly.
- `cd app/client && bun run build` — Production build of the client to catch any bundler-level errors.
- Read `.claude/commands/test_e2e.md`, then read and execute `.claude/commands/e2e/test_data_preview_inline_editing.md` to validate the feature end-to-end in a real browser via Playwright.

## Notes
- **No new Python or JS libraries required.** The implementation reuses FastAPI, the existing `sqlite3` connection pattern, `core/sql_security.py`, and the existing modal/CSS conventions on the client.
- **Why `rowid` instead of a primary-key column?** Files uploaded via `convert_csv_to_sqlite` / `convert_json_to_sqlite` use pandas' `to_sql`, which does not declare a primary key. SQLite's implicit `rowid` is always present for non-`WITHOUT ROWID` tables and is the safest stable identifier for UPDATE/DELETE without requiring schema changes to existing uploads.
- **Why bypass `validate_sql_query` for the write endpoints?** `validate_sql_query` is an aggressive denylist designed for LLM-generated free-form queries: it blocks `DELETE FROM`, `UPDATE ... SET`, and `INSERT ... SELECT` outright. Our new endpoints construct fixed SQL templates with validated identifiers and parameterized values — they are safe by construction. `execute_query_safely`'s identifier validation + the `allow_ddl=False` default block is sufficient.
- **NULL vs empty string on edit:** v1 stores the literal string from the cell, including `''`. A future enhancement could let users explicitly enter NULL (e.g., via a dropdown or `Ctrl+Delete`); out of scope here.
- **Type coercion on edit:** v1 sends edits as strings; SQLite's dynamic typing accepts them in TEXT columns and coerces for INTEGER/REAL columns. If the coercion fails, the server returns the SQLite error in the response's `error` field. A typed editor (number input for INTEGER columns, etc.) is a future enhancement.
- **Concurrent editors:** No optimistic locking. If two users edit the same row simultaneously, last-write-wins. Acceptable for the single-user local-dev positioning of this app.
- **Pagination defaults:** 50 rows per page (matches the issue). The endpoint accepts `1 <= limit <= 200` so power users could request a larger page via a manually crafted URL, but the UI always sends 50.
