# Application Analysis Report: Natural Language SQL Interface

## Overview

A full-stack web application that allows users to **upload data files and query them using natural language**, which gets converted to SQL via LLM (OpenAI GPT or Anthropic Claude). Users can upload CSV/JSON/JSONL files, ask questions in plain English, and get structured SQL results back.

---

## Technology Stack

| Layer | Technology | Details |
|-------|-----------|---------|
| **Frontend** | TypeScript 5.8 + Vite 6.3 | Vanilla TS, no framework (React/Vue/etc.) |
| **Backend** | Python 3.10+ + FastAPI 0.115 | Async web framework with Uvicorn ASGI server |
| **Database** | SQLite | File-based, embedded at `app/server/db/database.db` |
| **LLM** | OpenAI (GPT-4.1) + Anthropic (Claude Sonnet 4) | Dual provider support for NL-to-SQL conversion |
| **Data Processing** | Pandas 2.3 | CSV/JSON/JSONL ingestion and SQL operations |
| **Testing** | Pytest 8.4 | Server-side tests; no client-side tests |
| **Linting** | Ruff | Python code quality |
| **Package Mgmt** | uv (Python), npm (Node) | No monorepo tooling |

---

## Architecture

```
Browser (Vanilla TS + DOM)
    |
Vite Dev Server (localhost:5173) -- proxies /api
    |
FastAPI Backend (localhost:8000)
    +-- LLM Processor --> OpenAI / Anthropic APIs
    +-- SQL Processor --> SQLite
    +-- File Processor --> CSV/JSON/JSONL --> SQLite tables
    +-- SQL Security --> Injection prevention
    +-- Insights --> Statistical analysis
    +-- Export Utils --> CSV export
```

### Key Architectural Decisions

- Zero runtime dependencies on the client (only build-time TS + Vite)
- All business logic in a single `main.ts` with direct DOM manipulation
- No ORM -- raw SQL with parameterized queries
- No authentication -- relies on local/trusted deployment
- No Docker or CI/CD -- shell scripts for start/stop

### Project Structure

```
app/
+-- client/
|   +-- src/
|   |   +-- main.ts              # Entry point with all UI logic
|   |   +-- api/client.ts        # HTTP client for backend communication
|   |   +-- style.css            # Global styles (~540 lines)
|   |   +-- types.d.ts           # TypeScript interfaces
|   +-- public/sample-data/      # Demo datasets (users, products, events)
|   +-- index.html               # SPA entry point
|   +-- vite.config.ts           # Dev server + API proxy config
|   +-- tsconfig.json            # TypeScript configuration
|   +-- package.json             # Dependencies and scripts
|
+-- server/
    +-- core/
    |   +-- data_models.py       # Pydantic request/response models
    |   +-- file_processor.py    # CSV/JSON/JSONL to SQLite conversion
    |   +-- llm_processor.py     # LLM integration (OpenAI/Anthropic)
    |   +-- sql_processor.py     # SQL execution and schema retrieval
    |   +-- sql_security.py      # SQL injection prevention
    |   +-- insights.py          # Statistical analysis generation
    |   +-- export_utils.py      # CSV export functionality
    |   +-- constants.py         # Delimiter constants
    +-- db/                      # SQLite database files
    +-- tests/                   # Pytest test suite
    +-- server.py                # FastAPI application entry point
    +-- pyproject.toml           # Python project configuration
```

---

## Features

### Data Management

- **File upload** -- CSV, JSON, JSONL with drag-and-drop support
- **JSONL flattening** -- nested objects/arrays automatically flattened into columns
- **Sample datasets** -- built-in Users, Products, Events for quick start
- **Table management** -- view schema, export as CSV, delete tables

### Natural Language Querying

- **NL-to-SQL conversion** -- type a question in English, get SQL + results
- **Dual LLM support** -- choose between OpenAI (GPT-4.1) or Anthropic (Claude Sonnet)
- **Random query generation** -- auto-generate example queries based on current schema
- **Execution metrics** -- shows generated SQL, row count, execution time

### Data Analysis and Export

- **Column insights** -- unique values, nulls, min/max/avg, most common values
- **Schema visualization** -- tables with column types, row counts, data type indicators
- **CSV export** -- export query results or entire tables

### Security

- **SQL injection prevention** -- identifier validation, dangerous operation blocking, comment injection detection
- **Query restrictions** -- blocks DDL (DROP/CREATE/ALTER) and destructive DML (DELETE/UPDATE)
- **Input sanitization** -- table/column name validation via regex whitelist

---

## API Surface

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/upload` | Upload CSV/JSON/JSONL and create SQLite table |
| POST | `/api/query` | Natural language to SQL to results |
| GET | `/api/schema` | Get all table schemas |
| POST | `/api/insights` | Statistical analysis for columns |
| GET | `/api/generate-random-query` | Generate sample NL query |
| GET | `/api/health` | Health check with DB status |
| DELETE | `/api/table/{name}` | Delete a table |
| POST | `/api/export/table` | Export table as CSV |
| POST | `/api/export/query` | Export query results as CSV |

---

## Frontend Details

### UI/UX

- **No external UI library** -- pure CSS with custom component styling
- **CSS variables** for theming (primary: `#667eea`, secondary: `#764ba2`, background: `#E0F6FF`)
- **System font stack**: `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`
- Rounded corners, subtle shadows, smooth transitions
- Modal-based file upload with drag-and-drop
- Sticky table headers for result scrolling
- Responsive grid for sample data buttons
- Disabled state styling and loading spinners

### Key UI Components

1. **Query Input Section** -- textarea with gradient primary/secondary buttons, Cmd/Ctrl+Enter shortcut
2. **Results Section** -- SQL display box, results table with hover effects
3. **Tables Section** -- table cards showing schema with column tags
4. **Upload Modal** -- centered overlay with sample data quick-access buttons
5. **Notifications** -- inline error (red) and success (green) messages

### Client API Layer

- Thin HTTP client wrapper using native `fetch`
- Dynamic base URL: `/api` in dev (proxied), `VITE_BACKEND_URL` in production
- Debounced query execution (400ms)

---

## Server Details

### LLM Integration

- **OpenAI**: GPT-4.1 (model `gpt-4.1-2025-04-14`)
- **Anthropic**: Claude Sonnet 4 (model `claude-sonnet-4-0`)
- Schema context provided to LLM for accurate SQL generation
- Markdown cleanup from LLM responses
- Automatic comment stripping

### Data Import Pipeline

- **CSV**: Standard tabular format via `pd.read_csv`
- **JSON**: Array of objects
- **JSONL**: Line-delimited JSON with intelligent flattening (nested objects use `__` delimiter, arrays use `_` with indices)
- Automatic column name sanitization (lowercase, underscores)
- Bulk insert via Pandas `to_sql()`

### SQL Security Module

- Identifier validation with regex: `^[a-zA-Z_][a-zA-Z0-9_\s]*$`
- Whitelist-based SQL keyword blocking
- Safe identifier escaping with square brackets
- Parameterized queries for values
- Blocks: DROP, CREATE, ALTER, TRUNCATE, DELETE, INSERT...SELECT, UPDATE
- Comment injection detection (`--` and `/* */`)
- Common injection pattern detection

---

## Testing

Server-side tests cover:

- **File processing** -- CSV/JSON/JSONL conversion, column cleaning, edge cases
- **LLM processing** -- mocked OpenAI/Anthropic calls, schema formatting, markdown cleanup
- **SQL processing** -- query execution, schema retrieval, error handling
- **SQL injection** -- comprehensive security test suite (identifier validation, pattern detection)
- **Export** -- CSV generation, empty data handling

**Gap**: No client-side tests exist.

### Test Configuration

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_classes = "Test*"
python_functions = "test_*"
```

---

## Configuration

### Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `OPENAI_API_KEY` | OpenAI API access | Required |
| `ANTHROPIC_API_KEY` | Anthropic API access | Required |
| `FRONTEND_PORT` | Vite dev server port | 5173 |
| `BACKEND_PORT` | FastAPI server port | 8000 |
| `VITE_BACKEND_URL` | Backend URL for production client | `http://localhost:8000` |

### Running the Application

Startup via `scripts/start.sh` launches both servers:

1. Checks `.env` exists in `app/server/`
2. Kills existing processes on ports 8000 and 5173
3. Starts backend: `cd app/server && uv run python server.py`
4. Starts frontend: `cd app/client && npm run dev`

Teardown via `scripts/stop_apps.sh`.

### Build Scripts

```json
{
  "dev": "vite",
  "build": "tsc && vite build",
  "preview": "vite preview"
}
```

---

## Limitations and Considerations

- **No authentication** -- designed for local/trusted use only
- **SQLite** -- single-writer, not suitable for high concurrency
- **No caching** -- every query hits the LLM and database fresh
- **No pagination** -- full result sets loaded in memory
- **No containerization** -- no Docker support, manual setup required
- **No CI/CD** -- no automated pipeline
- **No connection pooling** -- single SQLite connections per request
- **API keys in plain text** -- stored in `.env` files
- **No rate limiting** -- no request throttling
