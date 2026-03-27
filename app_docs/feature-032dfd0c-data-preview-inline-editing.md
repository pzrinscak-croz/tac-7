# Data Preview with Inline Editing

**ADW ID:** 27
**Date:** 2026-03-27
**Specification:** specs/issue-032dfd0c-adw-27-sdlc_planner-data-preview-inline-editing.md

## Overview

Adds the ability to preview table data directly from the schema panel by clicking a table name. The preview opens a paginated modal (50 rows per page) where users can click any cell to edit it in place, add new rows, or delete existing rows. All changes persist back to the SQLite database, transforming the app from read-only querying into a full data management tool.

## What Was Built

- Clickable table names in the schema panel that open a data preview modal
- Paginated table preview (50 rows per page) with navigation controls
- Inline cell editing (click to edit, Enter to save, Escape to cancel)
- Add Row functionality with input fields for each column
- Delete Row functionality with confirmation dialog
- Four new REST API endpoints for table CRUD operations
- Pydantic request/response models for all new endpoints
- TypeScript interfaces and API client methods
- Server-side unit tests for all endpoints
- E2E test specification

## Technical Implementation

### Files Modified

- `app/server/core/data_models.py`: Added Pydantic models — `TablePreviewResponse`, `RowUpdateRequest`, `RowUpdateResponse`, `RowInsertRequest`, `RowInsertResponse`, `RowDeleteResponse`
- `app/server/server.py`: Added four new API endpoints — `GET /api/table/{table_name}/preview`, `PATCH /api/table/{table_name}/row`, `POST /api/table/{table_name}/row`, `DELETE /api/table/{table_name}/row/{rowid}`
- `app/client/src/types.d.ts`: Added TypeScript interfaces mirroring the server models
- `app/client/src/api/client.ts`: Added API client methods — `getTablePreview`, `updateRow`, `insertRow`, `deleteRow`
- `app/client/src/main.ts`: Added preview modal initialization, table rendering with pagination, inline cell editing, add/delete row logic, and wired table name clicks
- `app/client/src/style.css`: Added styles for preview modal, editable cells, pagination controls, new row inputs, delete buttons, and clickable table names
- `app/client/index.html`: Added preview modal HTML structure
- `app/server/tests/test_table_preview.py`: New unit tests for all four endpoints including error cases and SQL injection protection
- `.claude/commands/e2e/test_data_preview_inline_editing.md`: New E2E test specification

### Key Changes

- Uses SQLite `rowid` as the unique row identifier for all CRUD operations, with deduplication logic to handle INTEGER PRIMARY KEY aliases
- All database operations use `execute_query_safely` with parameterized queries and `validate_identifier` for SQL injection protection
- Inline editing uses blur-to-cancel behavior to prevent accidental saves when clicking away
- After any mutation (insert/delete), both the preview table and schema panel row counts are refreshed
- Preview modal is sized at 90vw to accommodate wide tabular data

## How to Use

1. Upload a data file (CSV, JSON, or JSONL) to create a table
2. In the schema panel, click any table name — it will show a pointer cursor and underline on hover
3. A preview modal opens showing the first 50 rows of data with column headers
4. Use Previous/Next buttons at the bottom to navigate pages
5. Click any cell to edit it — type a new value and press Enter to save, or Escape to cancel
6. Click "Add Row" at the top to insert a new row — fill in values and click Save
7. Click the × button on any row to delete it (a confirmation dialog will appear)
8. Close the modal with the × button, clicking outside, or pressing Escape

## Configuration

No additional configuration is required. The feature uses the existing SQLite database at `db/database.db`.

## Testing

- **Unit tests**: `cd app/server && uv run pytest` — includes tests in `test_table_preview.py` for all four endpoints, error handling, and SQL injection protection
- **Type checking**: `cd app/client && bun tsc --noEmit`
- **Build**: `cd app/client && bun run build`
- **E2E test**: Run the E2E test defined in `.claude/commands/e2e/test_data_preview_inline_editing.md`

## Notes

- SQLite `rowid` is reliable for all uploaded CSV/JSON/JSONL data since `WITHOUT ROWID` tables are not created by the app
- The `execute_query_safely` function allows DML operations; `validate_sql_query` is intentionally not used for write endpoints as it blocks UPDATE/DELETE/INSERT
- Concurrent edit safety is last-write-wins, which is acceptable for the single-user SQLite use case
