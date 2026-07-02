# Feature: Chart Visualization of Query Results

## Metadata
issue_number: `46`
adw_id: `b4247189`
issue_json: `{"number":46,"title":"1. Chart Visualization","body":"/feature\n\nadw_sdlc_iso\n\nmodel_set heavy\n\nAfter a query returns results, show a \"Visualize\" button. Renders data as a bar, line, or pie chart using Chart.js. User picks chart type and which columns to use for axes. The chart must display actual data values -- not empty charts, flat lines, or zero-height bars.\n\n**Scope:**\n- Client-only change -- add Chart.js dependency, chart type selector, axis dropdowns\n- Renders from the same data already in the results table\n\n**Acceptance criteria:**\n1. Y-axis dropdown only offers numeric columns; X-axis dropdown only offers categorical/text columns -- never allow non-numeric data on the Y-axis (it renders as zeros)\n2. Auto-select sensible defaults: first text column for X, first numeric column (excluding id/rowid) for Y\n3. If no numeric columns exist, show \"No numeric columns available\" instead of an empty chart\n4. Bar chart bars have heights proportional to data values; Y-axis auto-scales to fit the data\n5. Pie chart slices are proportional to values with percentage labels; max 15 slices (remainder grouped as \"Other\")\n6. All Y-axis values are parsed as numbers before charting -- never pass raw strings to Chart.js\n7. Tooltips show exact values on hover; legend and axis labels are visible\n8. Chart has minimum 300px height and is readable without scrolling\n9. If results table has 0 rows, the Visualize button is hidden"}`

## Feature Description
Add a client-side chart visualization capability to the Natural Language SQL Interface. After a query returns results, the user can click a **Visualize** button in the results header to open a chart panel below the results table. The panel lets the user pick a chart type (bar, line, or pie) and choose which result columns map to the X and Y axes, then renders the chart with [Chart.js](https://www.chartjs.org/).

The feature works entirely from the data already returned by `/api/query` and held in the results table — no backend changes are needed. The chart must display real data values (correctly parsed numeric magnitudes), auto-select sensible axis defaults, gracefully handle the absence of numeric columns, and remain readable (minimum 300px height, visible legend/axis labels, hover tooltips).

## User Story
As a data analyst using the Natural Language SQL Interface
I want to visualize my query results as a bar, line, or pie chart directly in the browser
So that I can quickly spot trends and comparisons without exporting the data to another tool

## Problem Statement
Query results are currently only shown as a raw HTML table. Understanding relationships, comparisons, and distributions from tabular numbers is slow and error-prone. Users have no built-in way to visualize their data and must export CSV and open a spreadsheet or BI tool. A naive charting implementation often produces useless charts — empty charts, flat lines, or zero-height bars — when non-numeric strings are passed to a chart library as values, or when the wrong columns are chosen for each axis.

## Solution Statement
Add a purely client-side visualization feature:
- Add the `chart.js` dependency to the client.
- After a successful, non-empty query, render a **Visualize** button in the existing results header button container (next to Export/Hide).
- Clicking **Visualize** reveals a chart panel containing: a chart-type selector (bar / line / pie), an X-axis dropdown, a Y-axis dropdown, and a `<canvas>` (minimum 300px height) wrapped in a fixed-height container.
- Robustly classify result columns into numeric vs. categorical by inspecting the actual data values (not relying on SQL type metadata, which the query response does not provide). The Y-axis dropdown offers only numeric columns; the X-axis dropdown offers only categorical/text columns.
- Auto-select defaults: first text column for X, first non-`id`/`rowid` numeric column for Y.
- If no numeric columns exist, show the message "No numeric columns available" instead of rendering an empty chart, and disable the chart controls.
- Always coerce Y values to numbers with a shared parse helper before handing them to Chart.js; skip/aggregate rows whose Y value is not a finite number.
- For pie charts, limit to a maximum of 15 slices, grouping the remainder into an "Other" slice, and show percentage labels via tooltips/legend.
- Destroy and recreate the Chart.js instance on every control change to avoid canvas reuse errors and stale charts.

The implementation keeps the existing vanilla-TS, function-based, DOM-building style in `main.ts` (no frameworks, no decorators) and adds styles that reuse existing CSS variables.

## Relevant Files
Use these files to implement the feature:

- `app/client/src/main.ts` - Main client logic. Contains `displayResults()` (where the Export/Hide buttons are added to `.results-header-buttons`) and `createResultsTable()`. The Visualize button and chart panel logic will be added here, hooked into `displayResults()`.
- `app/client/index.html` - Markup for the results section (`#results-section`, `.results-header`, `#results-container`). A chart panel container element will be added here (or created dynamically in `main.ts` following the existing dynamic-DOM pattern).
- `app/client/src/style.css` - Global styles using CSS variables (`--primary-color`, `--secondary-color`, `--success-color`, `.primary-button`, `.secondary-button`, `.results-header-buttons`). New styles for the Visualize button, chart panel, controls, and canvas container go here and must reuse existing variables.
- `app/client/src/types.d.ts` - Shared TypeScript interfaces mirroring the server Pydantic models. `QueryResponse` (with `results: Record<string, any>[]` and `columns: string[]`) is the data source for charts. Add any new chart-related types here if needed (e.g., a chart-type union, column classification result).
- `app/client/src/api/client.ts` - API client. Reference only; no changes required (feature is client-only and renders from data already in memory).
- `app/client/package.json` - Client dependencies. `chart.js` will be added here via `bun add chart.js`.
- `app/client/tsconfig.json` - TypeScript config used by `bun tsc --noEmit` and `bun run build`. Reference to ensure new code type-checks.
- `README.md` - Project overview, structure, and start/stop commands. Read first to understand the project and how to run client/server.
- `.claude/commands/conditional_docs.md` - Conditional documentation guide; consulted to decide which extra docs to read (client style + export feature doc are relevant).
- `app/client/src/style.css` (styling condition from `conditional_docs.md`) - Required reading because this feature changes client styling.
- `.claude/commands/test_e2e.md` - Read to understand how the E2E test runner executes test files, screenshot directory conventions, and output format.
- `.claude/commands/e2e/test_basic_query.md` - Read as the template/example for authoring a new E2E test file (structure: User Story, Test Steps, Success Criteria).
- `.claude/commands/e2e/test_export_functionality.md` - Additional E2E example showing how post-query UI buttons are tested; useful reference for the Visualize button test.

### New Files
- `.claude/commands/e2e/test_chart_visualization.md` - New E2E test file (created as a task in this plan) that validates the Visualize button appears after a non-empty query, that axis dropdowns are correctly populated, that a bar/line/pie chart renders with real data values, and that the button is hidden for empty results. Includes screenshots as proof.

## Implementation Plan
### Phase 1: Foundation
- Read `README.md`, `app/client/src/style.css`, and (per `conditional_docs.md`) the CSV export feature doc to understand existing post-query UI patterns.
- Add the `chart.js` dependency to the client with `bun add chart.js` (run in `app/client`).
- Add supporting TypeScript types in `types.d.ts` (chart-type union `'bar' | 'line' | 'pie'`, and a small interface describing classified columns) so the new code type-checks cleanly.
- Implement pure helper functions in `main.ts` for column classification and numeric parsing — these are the correctness core (they prevent empty charts / zero-height bars).

### Phase 2: Core Implementation
- Add a **Visualize** button into the existing `.results-header-buttons` container in `displayResults()`, shown only when `!response.error && response.results.length > 0` (hidden for 0 rows).
- Build the chart panel UI (chart-type selector + X/Y dropdowns + canvas container) that toggles open/closed when Visualize is clicked.
- Populate dropdowns: Y-axis with numeric columns only, X-axis with categorical/text columns only; auto-select defaults (first text column for X; first numeric column excluding `id`/`rowid` for Y).
- Implement `renderChart()` that reads the current selections, coerces Y values to numbers, builds Chart.js config for the chosen type, destroys any prior chart instance, and renders. Handle bar/line (numeric Y, auto-scaling axes) and pie (proportional slices, max 15 with "Other" grouping, percentage labels).
- Handle the "no numeric columns" case by showing the message and disabling controls instead of rendering.

### Phase 3: Integration
- Wire control-change events (chart type, X, Y) to re-render the chart.
- Ensure the chart panel is reset/recreated cleanly on each new query (destroy stale Chart.js instance, remove stale panel) so switching between queries never shows the previous chart.
- Add CSS for the button, panel, controls, and canvas container (min 300px height, readable) using existing CSS variables.
- Author the E2E test file and validate the full flow, then run all validation commands.

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

### 1. Research and read documentation
- Read `README.md` to confirm client/server run commands and structure.
- Read `.claude/commands/conditional_docs.md`; since this task changes client styling and adds post-query result UI, read `app/client/src/style.css` and `app_docs/feature-490eb6b5-one-click-table-exports.md`.
- Read `.claude/commands/test_e2e.md`, `.claude/commands/e2e/test_basic_query.md`, and `.claude/commands/e2e/test_export_functionality.md` to learn the E2E test file format.
- Re-read `app/client/src/main.ts` `displayResults()` and `createResultsTable()` to match the existing DOM-building style.

### 2. Add the Chart.js dependency
- In `app/client`, run `bun add chart.js` to add the dependency and update `package.json`/lockfile.
- Verify the import resolves: `import { Chart, registerables } from 'chart.js'` and `Chart.register(...registerables)` (or import the specific controllers/elements/scales needed for bar, line, pie). Prefer registering `registerables` for simplicity.

### 3. Add chart-related TypeScript types
- In `app/client/src/types.d.ts`, add:
  - `type ChartKind = 'bar' | 'line' | 'pie';`
  - An interface for classified columns, e.g. `interface ClassifiedColumns { numeric: string[]; categorical: string[]; }`.
- Keep types minimal and consistent with the file's existing style.

### 4. Implement column classification and numeric parsing helpers in `main.ts`
- Add a helper `parseNumericValue(value: any): number | null` that returns a finite number or `null`. Treat `null`/`''`/non-finite as `null`. Strip common formatting (e.g., leading currency symbols and thousands separators/commas) before `Number()` conversion so real numeric columns are not misclassified. Never return `NaN`.
- Add a helper `classifyColumns(results, columns): ClassifiedColumns`:
  - A column is **numeric** if it has at least one non-null value AND all non-null values parse to finite numbers via `parseNumericValue`.
  - Otherwise it is **categorical/text**.
  - Sample the full result set (or a bounded sample if very large) for classification.
- Add a helper to pick defaults:
  - Default X = first categorical column (fallback: first column overall if none categorical).
  - Default Y = first numeric column whose lowercased name is not `id` or `rowid`; if all numeric columns are `id`/`rowid`, fall back to the first numeric column.

### 5. Add the Visualize button in `displayResults()`
- In the block that currently adds the Export button to `.results-header-buttons` (only runs when `!response.error && response.results.length > 0`), also create a **Visualize** button:
  - `className = 'visualize-button secondary-button'`, label `📈 Visualize`, `title = 'Visualize results as a chart'`.
  - Insert it into the button container (before the toggle button, alongside Export).
- Because the button is only created inside the non-empty-results branch, it is inherently hidden when there are 0 rows (acceptance criterion 9). Confirm the empty/`No results found.` branch does not create it.
- Clicking Visualize toggles the chart panel visible/hidden and renders the chart on first open.

### 6. Build the chart panel UI
- Create (dynamically, following the existing pattern) a chart panel element appended to `#results-section` below `#results-container`. On each new `displayResults()` call, remove any existing panel and destroy any existing Chart instance to avoid duplicates/stale state.
- Panel contents:
  - A controls row with three labeled controls: Chart Type `<select>` (Bar, Line, Pie), X-Axis `<select>`, Y-Axis `<select>`.
  - A `<div class="chart-canvas-container">` wrapping a `<canvas id="results-chart">`. The container has a fixed height (>= 300px) and `position: relative` so Chart.js `maintainAspectRatio: false` fills it.
- Populate selects using the classification helpers:
  - Y-axis options = numeric columns only.
  - X-axis options = categorical columns only (fallback to all columns if none categorical).
  - Preselect the computed defaults.
- If `classifyColumns(...).numeric.length === 0`: render the message "No numeric columns available" inside the panel, do not create a chart, and disable/omit the chart-type and axis selects (acceptance criterion 3).

### 7. Implement `renderChart()`
- Read current selections (chart type, X column, Y column).
- Build labels from the X column (string values) and data from the Y column via `parseNumericValue`; drop rows whose Y parses to `null`.
- Destroy any existing `Chart` instance bound to the canvas before creating a new one (store the instance in a module-scoped variable).
- Bar/Line config:
  - `data.labels` = X values (as strings); `data.datasets[0].data` = parsed numeric Y values.
  - `type` = `'bar'` or `'line'`; ensure `scales.y.beginAtZero` appropriate and axes auto-scale to data (Chart.js default auto-scaling; do not hardcode a max). Add axis titles from column names.
  - Line chart: ensure points/line render actual values (not a flat line) — this follows directly from passing parsed numbers.
- Pie config:
  - Aggregate Y values by X label (sum) so duplicate categories combine.
  - Sort descending; if more than 15 categories, keep top 15 and group the remainder into a single "Other" slice summing the rest (acceptance criterion 5).
  - `type = 'pie'`; show a legend; configure a tooltip callback that displays the exact value and its percentage of the total.
- Common options for all types:
  - `responsive: true`, `maintainAspectRatio: false` (so the 300px container controls height).
  - Visible legend and axis labels; tooltips enabled showing exact values (acceptance criteria 7, 8).
- Re-render on any control `change` event.

### 8. Add styles in `style.css`
- Style `.visualize-button` consistently with the existing `.secondary-button` (reuse variables; no new color literals unless matching existing palette).
- Style the chart panel: spacing/border consistent with `.results-section`; a controls row using flexbox with labeled selects; `.chart-canvas-container { position: relative; min-height: 300px; height: 360px; width: 100%; }`.
- Ensure the panel is readable without horizontal scrolling on typical widths.

### 9. Handle edge cases and cleanup
- Ensure switching queries resets the panel: on `displayResults()`, remove the old panel and destroy the old chart instance so the previous query's chart never lingers.
- Ensure the panel starts hidden and only appears after clicking Visualize.
- Ensure changing to a chart type / axis combination with no valid numeric data shows the "No numeric columns available" state rather than an empty chart.
- Guard against `X` and `Y` selects being empty.

### 10. Create the E2E test file
- Create `.claude/commands/e2e/test_chart_visualization.md` modeled on `test_basic_query.md` and `test_export_functionality.md`. It must:
  - Navigate to the `Application URL` and verify core UI.
  - Load sample data (e.g., the Products sample, which has numeric `price`/quantity-like columns and a text name column) via the Upload modal.
  - Run a query that returns multiple rows with at least one numeric and one text column (e.g., "Show all products with their prices").
  - **Verify** the Visualize button appears in the results header.
  - Click **Visualize** and **Verify** the chart panel appears with a chart-type selector and X/Y dropdowns.
  - **Verify** the Y-axis dropdown contains a numeric column (e.g., price) and does not contain the text name column; **Verify** the X-axis dropdown contains the text column.
  - **Verify** a bar chart renders with non-zero bars (the canvas is present and Chart.js reports non-zero data — assert via visible bars / screenshot and, if feasible, `browser_evaluate` on chart data).
  - Switch to Pie and **Verify** the pie renders with slices.
  - Run an empty-result query (e.g., a filter that returns 0 rows) and **Verify** the Visualize button is hidden.
  - Capture screenshots at each key step (initial, results with Visualize button, bar chart, pie chart, empty-result state).
  - Include a `Success Criteria` section and the JSON `Output Format` block matching `test_e2e.md`.

### 11. Run validation
- Run all commands in the `Validation Commands` section and fix any failures until everything passes with zero regressions.
- Execute the new E2E test per `.claude/commands/test_e2e.md`.

## Testing Strategy
### Unit Tests
The client has no unit-test harness (Vite + TS, build-only scripts), so correctness is enforced primarily via TypeScript type-checking, the production build, and the E2E test. Where practical, structure the classification/parsing helpers as small pure functions so their behavior is easy to reason about and could be unit-tested later. Validate their behavior through the E2E test and manual verification:
- `parseNumericValue`: numbers, numeric strings, currency/comma-formatted strings → finite numbers; `null`/`''`/`'abc'` → `null`.
- `classifyColumns`: a column of all-numeric strings classifies as numeric; a column with any non-numeric value classifies as categorical.
- Server tests (`cd app/server && uv run pytest`) must still pass to confirm no regressions (feature is client-only).

### Edge Cases
- Query returns 0 rows → Visualize button is hidden.
- Query returns rows but no numeric columns (all text) → panel shows "No numeric columns available"; no empty chart.
- Only `id`/`rowid` numeric columns exist → default Y falls back to first numeric column; user can still chart it.
- Numeric column stored as strings (e.g., `"1200"`, `"$1,200.00"`) → parsed to real numbers, bars have proportional heights (not zero).
- Categorical X column with >15 distinct values in a pie chart → top 15 slices + "Other" remainder.
- Duplicate X labels in a pie chart → values aggregated (summed) per label.
- Switching chart type / axes repeatedly → no canvas-reuse errors; chart re-renders correctly (old instance destroyed).
- Running a new query after visualizing a previous one → old chart/panel removed; no stale chart.
- Null values within an otherwise numeric column → treated as missing (row dropped from that dataset), column still numeric.

## Acceptance Criteria
1. Y-axis dropdown lists only numeric columns; X-axis dropdown lists only categorical/text columns. Non-numeric data can never be selected for the Y-axis.
2. On opening the panel, X defaults to the first text column and Y defaults to the first numeric column excluding `id`/`rowid`.
3. When the result set has no numeric columns, the panel shows "No numeric columns available" and renders no empty chart.
4. Bar charts show bars with heights proportional to their values, and the Y-axis auto-scales to fit the data.
5. Pie charts show slices proportional to values with percentage labels, capped at 15 slices with the remainder grouped as "Other".
6. All Y-axis values are parsed to finite numbers (via `parseNumericValue`) before being passed to Chart.js — raw strings are never passed as data values.
7. Hovering a data point/slice shows a tooltip with the exact value; the legend and axis labels are visible.
8. The chart canvas container is at least 300px tall and the chart is readable without scrolling.
9. When the results table has 0 rows, the Visualize button is not shown.
10. `bun tsc --noEmit` and `bun run build` succeed; `uv run pytest` (server) passes with zero regressions; the new E2E test passes.

## Validation Commands
Execute every command to validate the feature works correctly with zero regressions.

- `cd app/client && bun install` - Ensure `chart.js` and all dependencies are installed.
- `cd app/client && bun tsc --noEmit` - Type-check the client to validate the new TypeScript compiles with zero errors.
- `cd app/client && bun run build` - Build the client (runs `tsc && vite build`) to validate a clean production build.
- `cd app/server && uv run pytest` - Run server tests to confirm the client-only change causes zero backend regressions.
- Read `.claude/commands/test_e2e.md`, then read and execute the new E2E test file `.claude/commands/e2e/test_chart_visualization.md` to validate the visualization flow end-to-end (Visualize button appears for non-empty results, dropdowns are correctly typed, bar/line/pie charts render real values, button hidden for empty results), capturing screenshots as proof.

## Notes
- **New dependency:** `chart.js` (added to `app/client` via `bun add chart.js`). This is the only new dependency; it is client-side and tree-shakeable. Register `registerables` once at module load, or import only the bar/line/pie controllers, elements, and scales to keep the bundle small.
- **Why classify from data, not schema:** the `/api/query` response (`QueryResponse`) provides only `columns: string[]` and `results: Record<string, any>[]` — no per-column SQL types. Therefore numeric vs. categorical must be inferred by inspecting the actual values, which also naturally satisfies acceptance criterion 6 (values are already parsed during classification and re-parsed at render time).
- **No frameworks / no decorators:** implementation stays in the existing vanilla-TS, function-based, imperative-DOM style of `main.ts`, consistent with the codebase conventions.
- **Chart instance lifecycle:** keep a single module-scoped `Chart` reference and always call `.destroy()` before creating a new chart or removing the panel, to avoid Chart.js "Canvas is already in use" errors.
- **Future considerations:** could add multi-series support (group by a second categorical column), downloadable chart image (Chart.js `toBase64Image`), and remembering the last-used chart type. Out of scope for this issue.
