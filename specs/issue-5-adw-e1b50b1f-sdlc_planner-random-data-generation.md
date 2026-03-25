# Feature: Table Random Data Generation Based on Schema Using LLMs

## Metadata
issue_number: `e1b50b1f`
adw_id: `{"number":5,"title":"Table Random Data Generation Based on Schema Using LLMs","body":"Generate synthetic data rows based on existing table patterns and schema\n\n/feature\n\nadw_sdlc_iso\n\nmodel_set heavy\n\nImplement a random data generation feature that creates synthetic data rows based on existing table patterns. Add a new button to the left of\nthe CSV export button in the Available Tables section nat triggers LLM-based data generation.\n\nImplementation details:\n- Add \"Generate Data\" button with appropriate icon next to each table (left of CSV export)\n- When clicked, sample 10 random existing rows from the table\n- Send sampled data + table schema to LLM with prompt to understand data patterns\n- Generate 10 new synthetic rows that match the patterns and constraints\n- Insert generated rows into the table with proper validation\n- Show success notification with count of rows added\n\nThe LLM should analyze:\n- Data types and formats for each column\n- Value ranges and distributions\n- Relationships between columns\n- Common patterns (emails, phone numbers, addresses, etc.)\n- Nullable vs required fields\n\nUpdate the Ul to show a loading state during generation and handle errors gracefully. The feature should use the existing LLM processor\nmodule and respect SQL security constraints.\n\nThis enhances testing and development by allowing users to quickly expand their datasets with realistic synthetic data.|"}`
issue_json: ``

## Feature Description
This feature adds an LLM-powered synthetic data generation capability to each table in the Available Tables section. When a user clicks the "Generate Data" button, the system samples 10 random existing rows from the table and sends them along with the full table schema to the LLM. The LLM analyzes data patterns (types, formats, ranges, relationships, common patterns like emails/phone numbers) and generates 10 new realistic synthetic rows that are then inserted into the table. This allows developers and testers to quickly expand datasets with realistic data without manually crafting test data.

## User Story
As a developer or tester
I want to generate synthetic data rows based on my existing table's schema and patterns
So that I can quickly expand datasets with realistic data for testing and development purposes

## Problem Statement
When working with small datasets, developers and testers need to expand their data for more comprehensive testing. Manually crafting realistic test data that matches existing patterns, formats, and constraints is time-consuming. There is no quick way to generate realistic synthetic data that respects column types, value ranges, and common data patterns (emails, phone numbers, etc.).

## Solution Statement
Add a "Generate Data" button to each table row in the Available Tables section (left of the CSV export button). When clicked, the system samples 10 existing rows, sends schema + sample data to the LLM, which generates 10 new synthetic rows matching the observed patterns. The rows are validated and inserted into the SQLite database using parameterized queries (bypassing the SQL query validator which blocks INSERT, since we build the INSERT ourselves). A success notification confirms how many rows were added.

## Relevant Files
Use these files to implement the feature:

- `app/server/core/data_models.py` — Add new Pydantic request/response models: `GenerateRandomDataRequest` and `GenerateRandomDataResponse`
- `app/server/core/llm_processor.py` — Add new functions: `generate_random_data_with_openai()`, `generate_random_data_with_anthropic()`, and `generate_random_data()` router; also read `app_docs/feature-4c768184-model-upgrades.md` for current model names
- `app/server/core/sql_processor.py` — Add `sample_random_rows()` helper to fetch 10 random existing rows from a table using `ORDER BY RANDOM() LIMIT 10`
- `app/server/core/sql_security.py` — Reference for identifier validation and escaping; use `validate_identifier()` and `escape_identifier()` for safe table/column name usage in INSERT construction
- `app/server/server.py` — Add new `POST /api/generate-random-data` endpoint that orchestrates sampling → LLM → validation → insertion
- `app/client/src/api/client.ts` — Add `generateRandomData(tableName: string)` API method
- `app/client/src/main.ts` — Update `displayTables()` to add "Generate Data" button left of CSV export button; add loading state and success notification logic
- `app/client/index.html` — No direct changes needed (buttons are injected dynamically by `main.ts`)
- `app/client/src/style.css` — Add `.generate-data-button` style for the new button; read this file for existing button class patterns; also read `app_docs/feature-490eb6b5-one-click-table-exports.md` for export button placement reference
- `app/server/tests/core/test_llm_processor.py` — Add unit tests for the three new LLM functions
- `app/server/tests/test_server.py` — Add integration tests for the new endpoint
- `README.md` — Read to understand project structure and commands

### New Files
- `.claude/commands/e2e/test_random_data_generation.md` — E2E test validating the full Generate Data button flow: click button, loading state, success notification, row count increase; read `.claude/commands/test_e2e.md` and `.claude/commands/e2e/test_basic_query.md` as references for format and structure

## Implementation Plan
### Phase 1: Foundation
Add backend data models and LLM functions to support random data generation. The LLM must return a JSON array of row objects, not SQL. This phase establishes the data contracts and LLM integration.

### Phase 2: Core Implementation
Implement the server endpoint that orchestrates: (1) validate table exists, (2) fetch schema, (3) sample 10 random rows, (4) call LLM, (5) parse and validate JSON response, (6) build parameterized INSERT statements for each row, (7) execute inserts, (8) return count. This phase must handle the security constraint that `validate_sql_query()` blocks INSERT — we build INSERT directly using `escape_identifier()` without going through the validator.

### Phase 3: Integration
Wire up the frontend: add API method, add "Generate Data" button in `displayTables()` left of the CSV export button, add loading/disabled state during generation, show success notification with row count on completion, handle errors gracefully.

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

### Step 1: Create E2E Test File
- Read `.claude/commands/test_e2e.md` to understand the E2E test framework and output format
- Read `.claude/commands/e2e/test_basic_query.md` as a reference for test file structure
- Create `.claude/commands/e2e/test_random_data_generation.md` with the following steps:
  1. Navigate to app, load the Users sample data
  2. Note the current row count for the users table in Available Tables
  3. Take a screenshot showing the "Generate Data" button next to the users table
  4. Click the "Generate Data" button for the users table
  5. Verify loading state appears on the button (disabled/spinner)
  6. Wait for the success notification to appear
  7. Take a screenshot of the success notification showing rows added count
  8. Verify the row count in Available Tables has increased by 10
  9. Take a screenshot of the updated table row count
  10. Run a query: "Show me all users" and verify results include the newly generated rows
  11. Take a final screenshot of the query results showing >20 rows

### Step 2: Add Pydantic Models
- Open `app/server/core/data_models.py`
- Add `GenerateRandomDataRequest` model with field `table_name: str`
- Add `GenerateRandomDataResponse` model with fields `rows_added: int` and `error: Optional[str] = None`

### Step 3: Add LLM Functions for Data Generation
- Open `app/server/core/llm_processor.py`
- Read `app_docs/feature-4c768184-model-upgrades.md` to confirm current model names (OpenAI: `gpt-4.1-2025-04-14`, Anthropic: `claude-sonnet-4-0`)
- Add `generate_random_data_with_openai(table_name: str, schema_info: dict, sample_rows: list[dict]) -> list[dict]`:
  - System prompt: instruct LLM to act as a data generation expert and return ONLY a valid JSON array
  - User prompt: include table name, schema (column names + types), sample rows, and instruction to generate exactly 10 new realistic rows matching observed patterns
  - Use `temperature=0.8` for creative variety
  - Parse response as JSON array; strip markdown code fences if present
  - Return list of dicts
- Add `generate_random_data_with_anthropic(table_name: str, schema_info: dict, sample_rows: list[dict]) -> list[dict]` with same signature and logic using Anthropic client
- Add `generate_random_data(table_name: str, schema_info: dict, sample_rows: list[dict]) -> list[dict]` router function following the same pattern as `generate_sql()` (check `OPENAI_API_KEY` first, fall back to `ANTHROPIC_API_KEY`)

### Step 4: Add `sample_random_rows` Helper to sql_processor
- Open `app/server/core/sql_processor.py`
- Add `sample_random_rows(db_path: str, table_name: str, limit: int = 10) -> list[dict]`:
  - Validate `table_name` using `validate_identifier()` from `sql_security`
  - Use `escape_identifier()` to safely build: `SELECT * FROM [table_name] ORDER BY RANDOM() LIMIT ?`
  - Execute using the existing sqlite3 connection pattern in the file
  - Return list of row dicts (using `row_factory = sqlite3.Row`)
  - Return empty list if table has 0 rows

### Step 5: Implement the Server Endpoint
- Open `app/server/server.py`
- Import `GenerateRandomDataRequest`, `GenerateRandomDataResponse`, `sample_random_rows`, `generate_random_data`
- Add `POST /api/generate-random-data` endpoint:
  1. Validate `table_name` using `validate_identifier()`; return 400 if invalid
  2. Check table exists using `check_table_exists()`; return 404 if not found
  3. Get full schema via `get_database_schema()`, extract schema for requested table
  4. Call `sample_random_rows()` to get up to 10 existing rows
  5. If table is empty (0 rows), return error: "Table must have at least 1 row to generate data"
  6. Call `generate_random_data(table_name, schema_info, sample_rows)`
  7. Validate LLM response is a list of dicts with correct column names (filter out any extra keys)
  8. For each generated row, build a parameterized INSERT: `INSERT INTO [table_name] ([col1], [col2], ...) VALUES (?, ?, ...)`
    - Use `escape_identifier()` for table and column names
    - Execute with value params (not identifier params) via raw sqlite3 connection
  9. Count successfully inserted rows
  10. Return `GenerateRandomDataResponse(rows_added=count)`
  11. Wrap in try/except; return error response on LLM or DB failures

### Step 6: Add API Client Method
- Open `app/client/src/api/client.ts`
- Add interface `GenerateRandomDataResponse { rows_added: number; error?: string; }`
- Add method `generateRandomData(tableName: string): Promise<GenerateRandomDataResponse>`:
  - POST to `/api/generate-random-data` with body `{ table_name: tableName }`
  - Return typed response
  - Follow same error handling pattern as existing methods

### Step 7: Add Generate Data Button to UI
- Open `app/client/src/main.ts`
- In `displayTables()`, locate where the CSV export button is created for each table
- Add a "Generate Data" button **left of** the CSV export button:
  - HTML: `<button class="generate-data-button" data-table="${table.name}" title="Generate 10 synthetic rows using AI">🎲 Generate</button>`
  - Add click event listener for each button
  - On click: disable button, set `button.innerHTML = '<span class="loading"></span> Generating...'`
  - Call `api.generateRandomData(tableName)`
  - On success: show notification `"✓ Added ${result.rows_added} rows to ${tableName}"`, reload schema via `loadDatabaseSchema()`
  - On error: show error via `displayError(result.error || 'Failed to generate data')`
  - In finally: re-enable button, restore button text to `'🎲 Generate'`

### Step 8: Add CSS Style for Generate Data Button
- Open `app/client/src/style.css`
- Read existing `.export-button` and `.toggle-button` styles for reference
- Add `.generate-data-button` style:
  - Background similar to secondary/accent color (e.g., purple gradient consistent with app theme `#667eea` to `#764ba2`)
  - White text, border-radius, padding consistent with other table action buttons
  - Hover state with slight opacity change
  - Disabled state with reduced opacity and `cursor: not-allowed`

### Step 9: Write Unit Tests for LLM Functions
- Open `app/server/tests/core/test_llm_processor.py`
- Add tests for `generate_random_data_with_openai()`:
  - Test successful generation returns a list of dicts
  - Test with mock OpenAI response returning JSON array
  - Test that markdown code fences are stripped from response
  - Test that temperature=0.8 is passed to API call
- Add tests for `generate_random_data_with_anthropic()` with same coverage
- Add tests for `generate_random_data()` router:
  - Routes to OpenAI when `OPENAI_API_KEY` is set
  - Routes to Anthropic when only `ANTHROPIC_API_KEY` is set
  - Raises error when neither key is set

### Step 10: Write Integration Tests for Endpoint
- Open `app/server/tests/test_server.py` (or create if it doesn't exist at `app/server/tests/test_server.py`)
- Add tests for `POST /api/generate-random-data`:
  - Returns 400 for invalid table name (SQL injection attempt)
  - Returns 404 when table doesn't exist
  - Returns error response when table is empty
  - Returns `rows_added: 10` on successful generation (mock LLM + DB)
  - Handles LLM returning malformed JSON gracefully

### Step 11: Run Validation Commands
- Execute all validation commands listed in the Validation Commands section to confirm zero regressions

## Testing Strategy
### Unit Tests
- `test_llm_processor.py`: Mock OpenAI/Anthropic clients, test JSON parsing, test markdown stripping, test temperature value, test router function key selection
- `test_server.py`: Mock `generate_random_data()` and DB functions, test all response paths (invalid table, missing table, empty table, success, LLM error)
- `test_sql_processor.py`: Test `sample_random_rows()` with a real in-memory SQLite DB, verify RANDOM() ordering, verify empty table returns []

### Edge Cases
- Table with 0 rows: return descriptive error ("Table must have at least 1 row to generate data")
- Table with 1–9 rows: sample all available rows (not exactly 10), still generate 10 new rows
- LLM returns malformed JSON: catch parse error, return error response
- LLM returns rows with extra/missing columns: filter to only schema columns; fill missing nullable columns with None
- LLM returns wrong data types (e.g., string for INTEGER column): attempt type coercion; on failure skip that row and log warning
- Table name with special characters: `validate_identifier()` rejects it, returns 400
- Very wide tables (50+ columns): LLM prompt may exceed token limits; truncate sample to fewer rows if needed
- Concurrent generate requests for same table: each inserts independently, no locking issues with SQLite

## Acceptance Criteria
- A "🎲 Generate" button appears to the left of the CSV export button for every table in the Available Tables section
- Clicking the button disables it and shows a loading indicator while generation is in progress
- After successful generation, a success notification appears showing exactly how many rows were added (should be 10)
- The table row count in Available Tables updates to reflect the newly added rows
- Generated rows are realistic and match observed column patterns (e.g., email columns contain valid email format, age columns contain plausible age ranges)
- Invalid or non-existent table names return an appropriate error response (400/404)
- Empty tables return a user-friendly error message
- All existing server tests continue to pass (`uv run pytest`)
- TypeScript compiles without errors (`bun tsc --noEmit`)
- Frontend builds successfully (`bun run build`)
- E2E test passes: button visible, loading state shown, success notification appears, row count increases by 10

## Validation Commands
Execute every command to validate the feature works correctly with zero regressions.

- Read `.claude/commands/test_e2e.md`, then read and execute `.claude/commands/e2e/test_random_data_generation.md` to validate the full Generate Data button flow end-to-end
- `cd app/server && uv run pytest` - Run server tests to validate the feature works with zero regressions
- `cd app/client && bun tsc --noEmit` - Run TypeScript type checking to validate the feature works with zero regressions
- `cd app/client && bun run build` - Run frontend build to validate the feature works with zero regressions

## Notes
- The existing `validate_sql_query()` in `sql_security.py` intentionally blocks INSERT statements to prevent LLM-generated SQL injection. For this feature, we bypass that validator by constructing parameterized INSERT statements directly — this is safe because we control the query construction and use `escape_identifier()` for names and parameter binding for values.
- The LLM prompt must explicitly request JSON output format and forbid SQL. Example system prompt: "You are a data generation expert. Return ONLY a valid JSON array of objects with no additional text, markdown, or SQL."
- Use `temperature=0.8` for data generation (same as random query generation) to get variety in generated values.
- If a table has fewer than 10 rows, pass all available rows as samples — the LLM can still infer patterns from fewer examples.
- The feature intentionally generates exactly 10 rows per click. Future iterations could add a configurable count via a modal.
- The `generate_random_data` LLM function should include the column data types explicitly in the prompt (e.g., "age: INTEGER", "email: TEXT") to help the LLM generate type-appropriate values.
- Consider adding a doc file at `app_docs/feature-e1b50b1f-random-data-generation.md` after implementation to document the feature for future reference (consistent with other feature docs in `app_docs/`).
