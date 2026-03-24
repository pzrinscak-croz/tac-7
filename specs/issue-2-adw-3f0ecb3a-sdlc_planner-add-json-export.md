# Feature: Add JSON Export

## Metadata
issue_number: `3f0ecb3a`
adw_id: `2`
issue_json: `{"number":2,"title":"Add json export","body":"feature - adw_sdic_iso - update to support table and query result 'ison' export. Similar to our csv export but specifically built for ison export."}`

## Feature Description
Add JSON export functionality that allows users to export database table data and query results as JSON files with a single click. This mirrors the existing CSV export feature but outputs well-structured JSON arrays of objects, making the data immediately consumable by JavaScript/TypeScript applications, REST APIs, and data processing pipelines.

## User Story
As a data analyst or developer
I want to export table data and query results as JSON files
So that I can use the structured data directly in applications, APIs, or tools that prefer JSON over CSV

## Problem Statement
The application currently supports CSV export for both tables and query results, but JSON is a widely preferred format for modern applications and APIs. Users who want to consume the exported data in JavaScript/TypeScript apps, REST clients, or NoSQL pipelines must manually convert CSV to JSON — adding unnecessary friction to their workflow.

## Solution Statement
Extend the existing export infrastructure (server-side `export_utils.py`, API endpoints in `server.py`, and client-side `client.ts` + `main.ts`) with JSON-specific export functions and UI buttons that mirror the CSV export pattern. The JSON output will be an array of objects where each object represents a row with column-name keys. No new dependencies are required since Python's built-in `json` module handles serialization.

## Relevant Files
Use these files to implement the feature:

- `app/server/core/export_utils.py` — Add `generate_json_from_data()` and `generate_json_from_table()` functions alongside the existing CSV counterparts
- `app/server/core/data_models.py` — Reuse existing `ExportRequest` and `QueryExportRequest` Pydantic models; no new models needed
- `app/server/server.py` — Add `POST /api/export/table-json` and `POST /api/export/query-json` endpoints following the same pattern as `/api/export/table` and `/api/export/query`
- `app/client/src/api/client.ts` — Add `exportTableAsJson()` and `exportQueryResultsAsJson()` API methods that download `.json` blobs
- `app/client/src/main.ts` — Add JSON export buttons in the table header and query results header, positioned alongside the existing CSV buttons
- `app/client/src/style.css` — Add any button styling needed for the new JSON export buttons (likely reusing existing export button classes)
- `app/server/tests/test_export_utils.py` — Extend with JSON-specific test cases alongside existing CSV tests
- `app_docs/feature-490eb6b5-one-click-table-exports.md` — Read to understand the full CSV export implementation details before implementing JSON export

### New Files
- `.claude/commands/e2e/test_json_export.md` — E2E test file validating JSON export buttons and file downloads for both table and query result exports
  - Read `.claude/commands/test_e2e.md` and `.claude/commands/e2e/test_basic_query.md` to understand how to create this E2E test file

## Implementation Plan
### Phase 1: Foundation
Add server-side JSON generation utilities and API endpoints, mirroring the CSV implementation exactly. Python's built-in `json` module will be used — no new dependencies needed.

### Phase 2: Core Implementation
Add client-side API methods and UI buttons for JSON export, positioning the JSON export buttons alongside the existing CSV buttons in both the table list and query results sections.

### Phase 3: Integration
Create the E2E test file and run full validation (unit tests, TypeScript type-check, build, and E2E tests) to confirm zero regressions.

## Step by Step Tasks

### Step 1: Add JSON export utility functions to `export_utils.py`
- Open `app/server/core/export_utils.py` and read the full file to understand existing patterns
- Add `generate_json_from_data(data: List[Dict[str, Any]], columns: List[str]) -> bytes`:
  - Accept `data` and `columns` parameters identical to `generate_csv_from_data`
  - Filter each row dict to only include the specified columns (same empty-data handling as CSV)
  - Serialize using `json.dumps(rows, default=str, indent=2)` and return as UTF-8 bytes
  - `default=str` handles non-serializable types (datetime, Decimal, etc.)
- Add `generate_json_from_table(conn: sqlite3.Connection, table_name: str) -> bytes`:
  - Use `pd.read_sql_query` to load the table into a DataFrame (same as CSV version)
  - Call `generate_json_from_data` with the DataFrame records and columns
  - Raise `ValueError` if the table does not exist (same guard as CSV version)
- Add `import json` at the top of the file

### Step 2: Add JSON export API endpoints to `server.py`
- Open `app/server/server.py` and locate the existing `/api/export/table` and `/api/export/query` endpoints
- Add `POST /api/export/table-json` endpoint:
  - Accept `ExportRequest` (reuse existing model — `table_name: str`)
  - Validate `table_name` with `validate_identifier()` and `check_table_exists()`
  - Call `generate_json_from_table(conn, request.table_name)`
  - Return `Response(content=json_data, media_type="application/json", headers={"Content-Disposition": f'attachment; filename="{request.table_name}_export.json"'})`
- Add `POST /api/export/query-json` endpoint:
  - Accept `QueryExportRequest` (reuse existing model — `data`, `columns`)
  - Call `generate_json_from_data(request.data, request.columns)`
  - Return `Response(content=json_data, media_type="application/json", headers={"Content-Disposition": 'attachment; filename="query_results.json"'})`
- Import `generate_json_from_table` and `generate_json_from_data` from `export_utils`

### Step 3: Add JSON export methods to `client.ts`
- Open `app/client/src/api/client.ts` and read the existing `exportTable` and `exportQueryResults` methods
- Add `exportTableAsJson(tableName: string): Promise<void>`:
  - `POST /api/export/table-json` with body `{ table_name: tableName }`
  - Extract filename from `Content-Disposition` header (default: `${tableName}_export.json`)
  - Create blob with `response.blob()`, create object URL, trigger download via `<a>` element, revoke URL
- Add `exportQueryResultsAsJson(data: any[], columns: string[]): Promise<void>`:
  - `POST /api/export/query-json` with body `{ data, columns }`
  - Download blob as `query_results.json`
  - Follow exact same blob-download pattern as the CSV version

### Step 4: Add JSON export buttons to `main.ts`
- Open `app/client/src/main.ts` and locate where CSV export buttons are rendered for tables and query results
- For the table list section: add a JSON export button immediately after the CSV export button
  - Label: `📄 JSON` (or similar icon matching the CSV button style)
  - On click: call `api.exportTableAsJson(table.name)` with error handling via `displayError()`
- For the query results section: add a JSON export button immediately after the CSV export button
  - Label: `${getDownloadIcon()} JSON Export` (or reuse a `getJsonDownloadIcon()` helper if needed)
  - On click: call `api.exportQueryResultsAsJson(response.results, response.columns)` with error handling

### Step 5: Add CSS styling for JSON export buttons (if needed)
- Open `app/client/src/style.css` and check if existing export button styles can be reused
- If the JSON buttons require distinct visual treatment, add minimal CSS targeting the new button class
- Keep styling consistent with the existing CSV export buttons

### Step 6: Write unit tests for JSON export utilities
- Open `app/server/tests/test_export_utils.py` and read the existing test structure
- Add a `TestGenerateJsonFromData` class with tests for:
  - Empty data list returns `[]` JSON
  - Single row with all basic types (int, float, str, bool, None)
  - Multiple rows with correct structure (array of objects)
  - Column filtering (only specified columns appear)
  - Non-serializable types (datetime) are coerced to strings via `default=str`
  - Unicode characters in values
- Add a `TestGenerateJsonFromTable` class with tests for:
  - Non-existent table raises `ValueError`
  - Empty table returns `[]` JSON
  - Table with data returns correct JSON array

### Step 7: Create E2E test file
- Read `.claude/commands/test_e2e.md` and `.claude/commands/e2e/test_basic_query.md` to understand the E2E test format
- Create `.claude/commands/e2e/test_json_export.md` with:
  - User Story: "As a user, I want to export table data and query results as JSON files"
  - Test Steps that:
    1. Navigate to the application
    2. Take a screenshot of the initial state showing JSON export buttons in the tables section
    3. Verify JSON export buttons are visible next to CSV buttons in the Available Tables section
    4. Click a JSON export button for an available table
    5. Verify a `.json` file download is triggered (check network response or download bar)
    6. Take a screenshot after table JSON export
    7. Execute a query that returns results
    8. Verify JSON export button is visible in the query results header
    9. Click the JSON export button in query results
    10. Verify a `query_results.json` download is triggered
    11. Take a final screenshot
  - Success Criteria listing all verification points
  - At least 3 screenshots required

### Step 8: Run validation commands
- Execute all commands listed in the `Validation Commands` section to verify zero regressions

## Testing Strategy
### Unit Tests
- `TestGenerateJsonFromData`: empty data, single/multiple rows, column filtering, type coercion (datetime → str), Unicode, None values
- `TestGenerateJsonFromTable`: non-existent table error, empty table, table with data
- All existing CSV tests must continue to pass

### Edge Cases
- Empty `data` list → returns valid JSON `[]`
- `columns` list empty or mismatched with data keys → gracefully filters or returns empty objects
- Non-JSON-serializable values (datetime, Decimal) → coerced to string via `default=str`
- Table with NULL values → serialized as JSON `null`
- Very long string values → no truncation
- Table name with special characters → blocked by existing `validate_identifier()` security check

## Acceptance Criteria
- JSON export button appears next to each table's CSV export button in the Available Tables section
- JSON export button appears next to the CSV export button in the query results header
- Clicking a table JSON export button downloads `{tablename}_export.json`
- Clicking the query results JSON export button downloads `query_results.json`
- Downloaded JSON files contain a valid JSON array of objects with column-name keys
- NULL/None database values appear as JSON `null`
- Non-serializable types (datetime) are coerced to strings without crashing
- All existing CSV export functionality continues to work unchanged
- All server unit tests pass (`uv run pytest`)
- TypeScript compiles without errors (`bun tsc --noEmit`)
- Client builds successfully (`bun run build`)
- E2E test `.claude/commands/e2e/test_json_export.md` passes

## Validation Commands
Execute every command to validate the feature works correctly with zero regressions.

- `cd app/server && uv run pytest tests/test_export_utils.py -v` — Run export utility tests (CSV + JSON) to confirm full test coverage
- `cd app/server && uv run pytest` — Run all server tests to validate zero regressions
- `cd app/client && bun tsc --noEmit` — Validate TypeScript types compile cleanly
- `cd app/client && bun run build` — Validate production build succeeds

Read `.claude/commands/test_e2e.md`, then read and execute `.claude/commands/e2e/test_json_export.md` to validate JSON export functionality works end-to-end.

## Notes
- No new Python dependencies needed — `json` is part of the standard library and pandas is already installed
- The `default=str` JSON serialization strategy matches the convention used in the server's existing query response serialization
- JSON export buttons should be visually distinct from CSV buttons (different label text) but use the same styling class to maintain UI consistency
- The feature documentation in `app_docs/feature-490eb6b5-one-click-table-exports.md` explicitly notes "Future enhancements could include JSON/Excel export options using the same infrastructure" — this feature fulfills that roadmap item
- Consider naming the download buttons consistently: if CSV uses `📊 CSV`, JSON could use `📄 JSON` to keep the pattern clear
