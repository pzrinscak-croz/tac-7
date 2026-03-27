# Feature: Data Preview with Inline Editing

## Metadata
issue_number: `032dfd0c`
adw_id: `27`
issue_json: ``

## Feature Description
Add the ability to preview table data directly from the schema panel by clicking a table name. The preview opens a paginated modal (50 rows per page) where users can click any cell to edit it in place, add new rows, or delete existing rows. All changes persist back to the SQLite database. This transforms the app from read-only querying into a full data management tool, letting users fix data issues without writing SQL.

## User Story
As a data analyst
I want to click a table name to preview and edit its data inline
So that I can inspect, correct, and manage my data without writing SQL queries

## Problem Statement
Currently, users can only view data by writing natural language queries. There is no way to browse table contents directly, and no way to modify data (insert, update, delete rows) through the UI. Users who spot incorrect data must use external tools to fix it.

## Solution Statement
Add four new API endpoints for paginated preview, row update, row insert, and row delete. On the client, make table names clickable to open a preview modal with an editable data grid. Cells become editable on click (Enter saves, Escape cancels). Add Row and Delete Row buttons allow full CRUD. Pagination controls navigate pages of 50 rows. After any mutation, refresh the schema panel row counts.

## Relevant Files
Use these files to implement the feature:

### Existing Files
- `README.md` — Project overview, startup commands, tech stack reference
- `app/server/server.py` — Add new API endpoints (preview, update, insert, delete) following existing route patterns
- `app/server/core/data_models.py` — Add Pydantic request/response models for new endpoints
- `app/server/core/sql_security.py` — Use `validate_identifier`, `escape_identifier`, `execute_query_safely`, `check_table_exists` for all new database operations
- `app/server/core/sql_processor.py` — Reference for database connection pattern (`sqlite3.connect("db/database.db")`)
- `app/server/tests/test_sql_injection.py` — Reference for test patterns; extend with tests for new endpoints
- `app/client/src/main.ts` — Add click handler on table names, preview modal logic, inline editing, pagination, add/delete row
- `app/client/src/api/client.ts` — Add API methods: `getTablePreview`, `updateRow`, `insertRow`, `deleteRow`
- `app/client/src/types.d.ts` — Add TypeScript interfaces for new request/response types
- `app/client/src/style.css` — Add styles for preview modal, editable cells, pagination controls, add/delete row buttons
- `app/client/index.html` — Add preview modal HTML structure
- `.claude/commands/test_e2e.md` — Reference for E2E test runner execution
- `.claude/commands/e2e/test_basic_query.md` — Reference for E2E test file format and patterns

### New Files
- `app/server/tests/test_table_preview.py` — Unit tests for all four new API endpoints
- `.claude/commands/e2e/test_data_preview_inline_editing.md` — E2E test for data preview and inline editing feature

## Implementation Plan
### Phase 1: Foundation
Add Pydantic data models for request/response types. Add the four new server API endpoints with proper security (parameterized queries, identifier validation). Add server unit tests to validate all endpoints.

### Phase 2: Core Implementation
Add TypeScript interfaces for the new API types. Add API client methods. Build the preview modal HTML structure. Implement the preview table with pagination. Implement inline cell editing (click to edit, Enter to save, Escape to cancel). Implement Add Row and Delete Row functionality.

### Phase 3: Integration
Wire table name clicks to open the preview modal. After any mutation (update, insert, delete), refresh the preview data and the schema panel row counts. Add CSS styling for all new UI elements. Create E2E test and run full validation.

## Step by Step Tasks

### Step 1: Add Pydantic models for new endpoints
- In `app/server/core/data_models.py`, add these models:
  - `TablePreviewResponse(BaseModel)`: columns (List[str]), rows (List[Dict[str, Any]]), total_rows (int), page (int), limit (int), total_pages (int), error (Optional[str])
  - `RowUpdateRequest(BaseModel)`: column (str), value (Any), rowid (int)
  - `RowUpdateResponse(BaseModel)`: success (bool), error (Optional[str])
  - `RowInsertRequest(BaseModel)`: values (Dict[str, Any])
  - `RowInsertResponse(BaseModel)`: success (bool), rowid (int), error (Optional[str])
  - `RowDeleteResponse(BaseModel)`: success (bool), error (Optional[str])

### Step 2: Add server API endpoints
- In `app/server/server.py`, add four new endpoints:
  - `GET /api/table/{table_name}/preview?page=1&limit=50`:
    - Validate table name with `validate_identifier`
    - Check table exists with `check_table_exists`
    - Count total rows: `SELECT COUNT(*) FROM {table}`
    - Fetch paginated data: `SELECT rowid, * FROM {table} LIMIT ? OFFSET ?`
    - Return `TablePreviewResponse` with columns, rows, pagination info
  - `PATCH /api/table/{table_name}/row`:
    - Accept `RowUpdateRequest` body (rowid, column, value)
    - Validate table name and column name with `validate_identifier`
    - Execute: `UPDATE {table} SET {column} = ? WHERE rowid = ?` using `execute_query_safely` with `params` and `identifier_params`
    - Commit and return `RowUpdateResponse`
  - `POST /api/table/{table_name}/row`:
    - Accept `RowInsertRequest` body (values dict)
    - Validate table name and all column names
    - Build parameterized INSERT: `INSERT INTO {table} ({col1}, {col2}, ...) VALUES (?, ?, ...)`
    - Commit and return `RowInsertResponse` with new rowid
  - `DELETE /api/table/{table_name}/row/{rowid}`:
    - Validate table name, validate rowid is a positive integer
    - Execute: `DELETE FROM {table} WHERE rowid = ?`
    - Commit and return `RowDeleteResponse`
- Import new models at top of `server.py`
- All endpoints must use `try/except` with proper HTTP error codes (400, 404, 500) following existing patterns

### Step 3: Add server unit tests
- Create `app/server/tests/test_table_preview.py`:
  - Use `pytest` fixture to create a temp SQLite database with test data (follow pattern from `test_sql_injection.py`)
  - Test `GET /api/table/{name}/preview`: correct data returned, pagination works (page 2 has different rows), total_pages is accurate
  - Test `PATCH /api/table/{name}/row`: cell value updates correctly, persists after re-read
  - Test `POST /api/table/{name}/row`: new row inserted, rowid returned, row count increases
  - Test `DELETE /api/table/{name}/row/{rowid}`: row removed, row count decreases
  - Test error cases: invalid table name (400), non-existent table (404), invalid column name (400), non-existent rowid
  - Test SQL injection attempts on table name, column name, and value parameters

### Step 4: Add TypeScript interfaces
- In `app/client/src/types.d.ts`, add:
  - `TablePreviewResponse`: columns, rows, total_rows, page, limit, total_pages, error?
  - `RowUpdateRequest`: column, value, rowid
  - `RowUpdateResponse`: success, error?
  - `RowInsertRequest`: values (Record<string, any>)
  - `RowInsertResponse`: success, rowid, error?
  - `RowDeleteResponse`: success, error?

### Step 5: Add API client methods
- In `app/client/src/api/client.ts`, add to `api` object:
  - `getTablePreview(tableName: string, page: number, limit: number): Promise<TablePreviewResponse>` — GET request with query params
  - `updateRow(tableName: string, request: RowUpdateRequest): Promise<RowUpdateResponse>` — PATCH request
  - `insertRow(tableName: string, request: RowInsertRequest): Promise<RowInsertResponse>` — POST request
  - `deleteRow(tableName: string, rowid: number): Promise<RowDeleteResponse>` — DELETE request

### Step 6: Add preview modal HTML
- In `app/client/index.html`, add a new modal after the upload modal:
  ```html
  <div id="preview-modal" class="modal" style="display: none;">
    <div class="modal-content preview-modal-content">
      <div class="modal-header">
        <h2 id="preview-modal-title">Table Preview</h2>
        <button class="close-modal" id="close-preview-modal">&times;</button>
      </div>
      <div class="modal-body">
        <div id="preview-toolbar">
          <button id="add-row-button" class="primary-button">Add Row</button>
        </div>
        <div id="preview-table-container"></div>
        <div id="preview-pagination">
          <button id="prev-page-button" class="secondary-button" disabled>Previous</button>
          <span id="page-info">Page 1 of 1</span>
          <button id="next-page-button" class="secondary-button" disabled>Next</button>
        </div>
      </div>
    </div>
  </div>
  ```

### Step 7: Implement preview modal and inline editing in main.ts
- Add `openTablePreview(tableName: string)` function:
  - Call `api.getTablePreview(tableName, 1, 50)`
  - Render a data table inside `#preview-table-container` with column headers and rows
  - Include a hidden `rowid` column for tracking (not displayed but stored as `data-rowid` attribute on each `<tr>`)
  - Show the modal with title "Preview: {tableName}"
  - Track current state: `currentPreviewTable`, `currentPage`, `totalPages`
- Add inline cell editing:
  - On `<td>` click: replace cell content with an `<input>` pre-filled with current value, focus it
  - On `Enter` keypress: call `api.updateRow(tableName, { rowid, column, value: input.value })`, on success replace input with new text value
  - On `Escape` keypress: revert input to original text (cancel edit)
  - On input `blur`: same as Escape (cancel edit to avoid accidental saves)
- Add pagination:
  - Wire `#prev-page-button` and `#next-page-button` to fetch appropriate page
  - Update `#page-info` text: "Page X of Y"
  - Disable prev on page 1, disable next on last page
- Add "Add Row" button:
  - On click: insert a new row at the top of the table with empty `<input>` fields for each column (except rowid)
  - Include a "Save" button in the row that calls `api.insertRow(tableName, values)`
  - On success: reload the current page preview, refresh schema panel via `loadDatabaseSchema()`
- Add "Delete Row" button:
  - Add a delete button (×) in the last column of each row
  - On click: show `confirm()` dialog: "Are you sure you want to delete this row?"
  - On confirm: call `api.deleteRow(tableName, rowid)`, reload preview, refresh schema panel
- Wire table name click in `displayTables()`:
  - Make `tableName` element clickable (add cursor pointer style)
  - Add click handler: `tableName.onclick = () => openTablePreview(table.name)`
- Add modal close logic:
  - Close button click, background click, Escape key

### Step 8: Add CSS styles
- In `app/client/src/style.css`, add styles for:
  - `.preview-modal-content`: wider modal (max-width: 90vw, max-height: 85vh, overflow auto)
  - `.preview-table`: full-width table with borders, styled like `.results-table`
  - `.preview-table td[contenteditable]` or input styling for editable cells
  - `.preview-table td.editing`: highlight border/background for cell being edited
  - `.preview-table td:hover`: subtle hover effect to indicate clickability
  - `#preview-pagination`: flex container, centered, gap between elements
  - `#preview-toolbar`: flex container with Add Row button
  - `.delete-row-button`: small red × button in each row
  - `.table-name`: add `cursor: pointer` and hover underline to indicate clickability
  - `.new-row-input`: styling for input fields in new row

### Step 9: Create E2E test file
- Create `.claude/commands/e2e/test_data_preview_inline_editing.md` with the following structure:
  - **User Story**: As a user, I want to preview and edit table data inline so I can manage my data visually
  - **Test Steps**:
    1. Navigate to the Application URL
    2. Take screenshot of initial state
    3. Verify a table exists in the Available Tables section (upload sample data if needed)
    4. Click the table name to open preview modal
    5. Take screenshot of the preview modal showing data with column headers
    6. Verify pagination shows "Page 1 of Y" and data rows are visible
    7. Click "Next" to go to page 2 (if table has >50 rows), verify different rows shown
    8. Click a cell to enter edit mode — verify input appears with current value
    9. Type a new value and press Enter — verify cell updates
    10. Take screenshot showing the edited cell
    11. Click "Add Row" button — verify empty input row appears
    12. Fill in values and click Save — verify new row appears in table
    13. Take screenshot showing the new row
    14. Click Delete button on a row — verify confirmation dialog appears
    15. Confirm deletion — verify row is removed
    16. Take screenshot of final state
    17. Close preview modal
    18. Verify schema panel row count has updated
  - **Success Criteria**: Preview opens with correct data, pagination works, inline editing persists, add/delete rows work, row count updates

### Step 10: Run validation
- Run all validation commands to ensure zero regressions
- Run the E2E test to validate the feature end-to-end

## Testing Strategy
### Unit Tests
- Test `GET /api/table/{name}/preview` returns correct paginated data with proper column headers
- Test pagination math: total_pages = ceil(total_rows / limit)
- Test `PATCH /api/table/{name}/row` updates the correct cell and persists
- Test `POST /api/table/{name}/row` inserts a new row and returns the new rowid
- Test `DELETE /api/table/{name}/row/{rowid}` removes the row
- Test all endpoints reject invalid table names (SQL injection protection)
- Test all endpoints reject non-existent tables with 404
- Test PATCH rejects invalid column names
- Test DELETE rejects non-integer rowid values

### Edge Cases
- Table with 0 rows: preview should show headers but no data, pagination shows "Page 0 of 0"
- Table with exactly 50 rows: should be 1 page, next button disabled
- Table with 51 rows: should be 2 pages, page 2 shows 1 row
- Editing a cell to empty string (should be allowed — stores empty string)
- Editing a cell to NULL-like value
- Adding a row with missing columns (should insert with NULL for missing)
- Deleting the last row on a page (should navigate to previous page if current page is now empty)
- Table names with spaces or special valid characters
- Very long cell values (should not break layout)
- Concurrent edits (last write wins — acceptable for single-user SQLite)
- Columns with types that need careful handling (BLOB, DATE)

## Acceptance Criteria
1. Clicking a table name in the schema panel opens a preview modal showing correct data with column headers
2. Pagination works: page 2 shows different rows; "Page X of Y" is accurate
3. Clicking a cell makes it editable; Enter saves the new value; Escape reverts without saving
4. Edited values persist after closing and re-opening the preview (page refresh)
5. "Add Row" inserts a visible new row that persists after refresh
6. "Delete Row" asks for confirmation via confirm() dialog, then removes the row permanently
7. Schema panel row count updates after adding or deleting rows
8. All server unit tests pass with zero failures
9. TypeScript compiles with no errors
10. Client builds successfully

## Validation Commands
Execute every command to validate the feature works correctly with zero regressions.

- `cd app/server && uv run pytest` - Run server tests to validate the feature works with zero regressions
- `cd app/client && bun tsc --noEmit` - Run frontend type checking to validate no TypeScript errors
- `cd app/client && bun run build` - Run frontend build to validate the feature compiles correctly
- Read `.claude/commands/test_e2e.md`, then read and execute `.claude/commands/e2e/test_data_preview_inline_editing.md` E2E test file to validate this functionality works end-to-end

## Notes
- SQLite `rowid` is used as the unique row identifier for all CRUD operations. Every SQLite table has an implicit `rowid` column unless created with `WITHOUT ROWID`. This is reliable for the uploaded CSV/JSON/JSONL data in this app.
- The `execute_query_safely` function in `sql_security.py` blocks DDL by default but allows DML (INSERT, UPDATE, DELETE) since it only checks for DDL prefixes (DROP, CREATE, ALTER, TRUNCATE). However, `validate_sql_query` blocks UPDATE/DELETE/INSERT — we must NOT use `validate_sql_query` for the new write endpoints; use `execute_query_safely` directly with parameterized queries.
- The preview modal should be wider than the upload modal to accommodate tabular data — use max-width: 90vw.
- Blur on the edit input should cancel the edit (revert), not save. This prevents accidental saves when clicking away.
- No new libraries are needed. All functionality uses existing FastAPI, sqlite3, and vanilla TypeScript.
