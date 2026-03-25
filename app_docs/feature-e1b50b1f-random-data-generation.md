# Random Data Generation

**ADW ID:** e1b50b1f
**Date:** 2026-03-25
**Specification:** specs/issue-5-adw-e1b50b1f-sdlc_planner-random-data-generation.md

## Overview

This feature adds an LLM-powered synthetic data generation button to each table in the Available Tables section. When clicked, it samples up to 10 existing rows, sends them with the table schema to an LLM, and inserts 10 new realistic synthetic rows into the table. This allows developers and testers to quickly expand small datasets with realistic data.

## What Was Built

- `🎲 Generate` button added to every table row in the Available Tables section (left of the CSV export button)
- Loading/disabled state on the button during generation
- Success notification showing how many rows were added (auto-dismisses after 4 seconds)
- `POST /api/generate-random-data` server endpoint orchestrating sampling → LLM → validation → insertion
- `generate_random_data()` LLM router and provider-specific functions for OpenAI and Anthropic
- `sample_random_rows()` helper using `ORDER BY RANDOM() LIMIT ?` for sampling
- Parameterized INSERT construction that bypasses the SQL validator (safe via `escape_identifier()`)
- Unit tests for all new LLM functions and integration tests for the new endpoint

## Technical Implementation

### Files Modified

- `app/server/core/data_models.py`: Added `GenerateRandomDataRequest` and `GenerateRandomDataResponse` Pydantic models
- `app/server/core/llm_processor.py`: Added `generate_random_data_with_openai()`, `generate_random_data_with_anthropic()`, `generate_random_data()` router, and `_parse_json_array_response()` helper
- `app/server/core/sql_processor.py`: Added `sample_random_rows()` helper
- `app/server/server.py`: Added `POST /api/generate-random-data` endpoint with full orchestration logic
- `app/client/src/api/client.ts`: Added `generateRandomData(tableName)` API method and `GenerateRandomDataResponse` interface
- `app/client/src/main.ts`: Added Generate Data button in `displayTables()` with click handler, loading state, and success notification
- `app/client/src/style.css`: Added `.generate-data-button` styles with purple gradient theme, hover, and disabled states
- `app/client/src/types.d.ts`: Added type declarations for the new API response
- `app/server/tests/core/test_llm_processor.py`: Added unit tests for all three new LLM functions
- `app/server/tests/test_server.py`: Added integration tests for the new endpoint

### Key Changes

- **Security**: INSERT statements are constructed directly using `escape_identifier()` for names and parameterized binding for values — bypassing `validate_sql_query()` which blocks INSERT (by design) while remaining safe
- **LLM prompt**: Uses `temperature=0.8` for variety; explicitly requests JSON-only output; includes column names with data types so the LLM generates type-appropriate values
- **JSON parsing**: `_parse_json_array_response()` strips markdown code fences before parsing, handling LLMs that wrap output in ` ```json ` blocks
- **Error isolation**: Each row insert is wrapped in its own try/except; failures skip that row with a warning rather than aborting the entire batch
- **Empty table guard**: Returns a user-friendly error if the table has 0 rows (nothing to sample patterns from)

## How to Use

1. Upload a CSV/JSON file or use an existing database with at least one table containing data
2. In the **Available Tables** section, find the table you want to expand
3. Click the `🎲 Generate` button to the left of the CSV export button
4. Wait for the loading indicator — the button is disabled during generation
5. A green success notification confirms how many rows were added (typically 10)
6. The table row count updates automatically to reflect the new rows

## Configuration

No additional configuration required. The feature uses the same LLM API keys as the rest of the application:

- `OPENAI_API_KEY` — used first if set (model: `gpt-4.1-2025-04-14`)
- `ANTHROPIC_API_KEY` — fallback if OpenAI key is not set (model: `claude-sonnet-4-0`)

Both keys are set via the existing environment variable configuration.

## Testing

```bash
# Run server unit and integration tests
cd app/server && uv run pytest

# TypeScript type checking
cd app/client && bun tsc --noEmit

# Frontend build
cd app/client && bun run build
```

E2E test: `.claude/commands/e2e/test_random_data_generation.md` — validates the full flow: button visibility, loading state, success notification, row count increase.

## Notes

- Generates exactly 10 rows per click regardless of how many sample rows are available
- If the table has 1–9 rows, all available rows are used as samples (LLM can still infer patterns)
- The LLM validator bypassing is intentional and safe: we control INSERT construction end-to-end
- Future iterations could add a configurable row count via a modal dialog
