# JSON Export for Tables and Query Results

**ADW ID:** 2 (3f0ecb3a)
**Date:** 2026-03-25
**Specification:** specs/issue-2-adw-3f0ecb3a-sdlc_planner-add-json-export.md

## Overview

This feature extends the existing CSV export infrastructure to support JSON export for both database tables and query results. Users can now download data as well-structured JSON arrays of objects — making exports immediately consumable by JavaScript/TypeScript applications, REST APIs, and data processing pipelines without manual CSV-to-JSON conversion.

## What Was Built

- `generate_json_from_data()` utility function for serializing row data to JSON bytes
- `generate_json_from_table()` utility function for exporting a full SQLite table as JSON
- `POST /api/export/table-json` API endpoint for table JSON export
- `POST /api/export/query-json` API endpoint for query result JSON export
- `exportTableAsJson()` client API method with blob download
- `exportQueryResultsAsJson()` client API method with blob download
- JSON export buttons (`📄 JSON`) in the Available Tables section alongside CSV buttons
- JSON export buttons (`📄 JSON Export`) in the query results header alongside CSV buttons
- Unit tests covering empty data, multiple rows, column filtering, type coercion, NULL handling

## Technical Implementation

### Files Modified

- `app/server/core/export_utils.py`: Added `generate_json_from_data()` and `generate_json_from_table()` functions; added `import json` and `Any` to typing imports
- `app/server/server.py`: Added `POST /api/export/table-json` and `POST /api/export/query-json` endpoints; imported the new JSON utility functions
- `app/client/src/api/client.ts`: Added `exportTableAsJson()` and `exportQueryResultsAsJson()` methods using the same blob-download pattern as CSV
- `app/client/src/main.ts`: Added JSON export buttons in both the table list and query results sections
- `app/server/tests/test_export_utils.py`: Added `TestGenerateJsonFromData` and `TestGenerateJsonFromTable` test classes

### Key Changes

- JSON serialization uses `json.dumps(rows, default=str, indent=2)` — the `default=str` fallback handles non-serializable types (datetime, Decimal) without crashing
- `generate_json_from_table()` uses `df.astype(object).where(df.notna(), other=None)` to convert pandas NaN to Python `None`, ensuring SQLite NULL values serialize as JSON `null` rather than `NaN`
- API endpoints reuse existing `ExportRequest` and `QueryExportRequest` Pydantic models — no new data models needed
- Client blob-download logic is identical to the CSV implementation: `fetch` → `response.blob()` → object URL → `<a>` click → revoke URL
- No new Python dependencies required; `json` is part of the standard library

## How to Use

**Export a table as JSON:**
1. Navigate to the Available Tables section
2. Click the `📄 JSON` button next to the desired table
3. The browser downloads `{tablename}_export.json`

**Export query results as JSON:**
1. Execute a SQL query that returns results
2. In the query results header, click `📄 JSON Export`
3. The browser downloads `query_results.json`

**JSON output format:**
```json
[
  { "column1": "value1", "column2": 42, "column3": null },
  { "column1": "value2", "column2": 99, "column3": "text" }
]
```

## Configuration

No additional configuration required. The feature uses the same database connection and security validation (`validate_identifier`, `check_table_exists`) as the existing CSV export endpoints.

## Testing

Run unit tests:
```bash
cd app/server && uv run pytest tests/test_export_utils.py -v
```

Run all server tests to verify zero regressions:
```bash
cd app/server && uv run pytest
```

Validate TypeScript and client build:
```bash
cd app/client && bun tsc --noEmit
cd app/client && bun run build
```

## Notes

- This feature fulfills the roadmap item noted in `app_docs/feature-490eb6b5-one-click-table-exports.md`: "Future enhancements could include JSON/Excel export options using the same infrastructure"
- JSON export buttons use the same CSS class (`export-button`) as CSV buttons for visual consistency
- The `default=str` serialization strategy matches the convention already used in the server's query response serialization
