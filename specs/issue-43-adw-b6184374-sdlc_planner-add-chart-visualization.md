# Feature: Chart Visualization for Query Results

## Metadata
issue_number: `43`
adw_id: `b6184374`
issue_json: `{"number":43,"title":"1. Chart Visualization","body":"/feature\n\nadw_sdlc_iso\n\nmodel_set heavy\n\nAfter a query returns results, show a \"Visualize\" button. Renders data as a bar, line, or pie chart using Chart.js. User picks chart type and which columns to use for axes. The chart must display actual data values -- not empty charts, flat lines, or zero-height bars.\n\n**Scope:**\n- Client-only change -- add Chart.js dependency, chart type selector, axis dropdowns\n- Renders from the same data already in the results table\n\n**Acceptance criteria:**\n1. Y-axis dropdown only offers numeric columns; X-axis dropdown only offers categorical/text columns -- never allow non-numeric data on the Y-axis (it renders as zeros)\n2. Auto-select sensible defaults: first text column for X, first numeric column (excluding `id`/`rowid`) for Y\n3. If no numeric columns exist, show \"No numeric columns available\" instead of an empty chart\n4. Bar chart bars have heights proportional to data values; Y-axis auto-scales to fit the data\n5. Pie chart slices are proportional to values with percentage labels; max 15 slices (remainder grouped as \"Other\")\n6. All Y-axis values are parsed as numbers before charting -- never pass raw strings to Chart.js\n7. Tooltips show exact values on hover; legend and axis labels are visible\n8. Chart has minimum 300px height and is readable without scrolling\n9. If results table has 0 rows, the Visualize button is hidden"}`

## Feature Description
Add a client-side chart visualization feature to the Natural Language SQL Interface. After a query returns results, the user sees a "Visualize" button alongside the existing Export/Hide buttons. Clicking it reveals a chart panel that renders the query result data as a bar, line, or pie chart using Chart.js. The user picks the chart type and the X / Y axis columns via dropdowns; the chart re-renders whenever any of those selections change. The same data already loaded in the results table powers the chart — no new server endpoint, no extra fetch.

The implementation is defensive about data types: only numeric columns are offered for the Y-axis, only text/categorical columns are offered for the X-axis, all Y values are parsed as numbers before being handed to Chart.js, and a clear empty state is shown when no numeric columns are available. Pie charts cap at 15 slices and group the remainder as "Other" to stay readable.

## User Story
As a data analyst
I want to visualize query results as a bar, line, or pie chart with one click
So that I can spot trends and shapes in the data without exporting to a separate tool

## Problem Statement
Today, query results are only displayed as a tabular grid. To see distribution, trends, or comparisons, the user has to read rows manually, export to CSV, and open Excel / a BI tool. There is no in-app way to visually inspect the result set. Worse, naive chart implementations frequently render broken charts (flat lines, zero-height bars, empty pies) when the user picks a non-numeric column for the Y axis or when values arrive as strings — so the UX must actively prevent those failure modes rather than letting the user discover them.

## Solution Statement
Add a client-only chart visualization module that:

1. Adds Chart.js as a frontend dependency (`bun add chart.js`).
2. Adds a "Visualize" button to the results header, next to Export and Hide. The button is only shown when there is at least one row of data.
3. When clicked, reveals a chart panel inside the results section containing:
   - A chart type selector (Bar / Line / Pie).
   - An X-axis dropdown (categorical / text columns only).
   - A Y-axis dropdown (numeric columns only).
   - A `<canvas>` host (min-height 300px) where Chart.js draws.
4. Detects column types by inspecting the actual values in `response.results` — a column is numeric if at least one non-null value is a finite number after `Number()` coercion, and it is not the `id` / `rowid` column. Everything else is categorical.
5. Auto-selects sensible defaults (first text column for X, first non-`id`/`rowid` numeric column for Y) on first open and re-opens when the user runs a new query.
6. Re-renders the chart on any selector change. All Y-axis values are coerced with `Number()` and filtered for `Number.isFinite` before being handed to Chart.js. Strings, nulls, and NaNs become safely excluded (with the corresponding row dropped, not silently coerced to 0).
7. Caps pie charts at 15 slices, summing the remainder into a single "Other" slice. Bar charts auto-scale via Chart.js's default `beginAtZero: true` plus auto-bounds.
8. Shows the empty state "No numeric columns available" if the result set has no numeric columns, in place of the chart canvas.
9. Tears down the previous Chart.js instance before drawing a new one (Chart.js requires `chart.destroy()` to avoid canvas reuse errors).

## Relevant Files
Use these files to implement the feature:

- `README.md` — Project overview and dev/build commands; read first to ground yourself in how the client is built and how it relates to the server.
- `app/client/index.html` — Where the results-section markup lives; the chart panel container will sit inside `#results-section`.
- `app/client/src/main.ts` — All current client logic lives here as plain functions (no framework). The Visualize button is added next to the Export button inside `displayResults()` (around lines 226–261), and the new chart panel rendering / wiring code is added in this same file as new functions.
- `app/client/src/style.css` — Where the chart panel layout, controls row, and canvas sizing rules belong (preserve existing `:root` palette).
- `app/client/src/types.d.ts` — Holds the global ambient types (`QueryResponse`, `TableSchema`). No new interface should leak server-side; any new types stay local to `main.ts`.
- `app/client/package.json` — Where the new `chart.js` runtime dependency will be added by `bun add chart.js`.
- `app/client/src/api/client.ts` — Reference only; confirms there is no new API call needed for this feature (everything is client-side).
- `.claude/commands/e2e/test_basic_query.md` — Reference for how an E2E test file is structured (User Story, Test Steps, Success Criteria, screenshots, etc.).
- `.claude/commands/e2e/test_export_functionality.md` — Reference for a button-driven E2E test that interacts with the results header (mirrors the Visualize button placement closely).
- `.claude/commands/test_e2e.md` — Read to understand how the E2E test runner consumes the test files (test runner, screenshot directory, output format).

### New Files
- `app/client/src/chart.ts` — New module that encapsulates chart rendering: column-type detection, default-axis selection, pie-slice capping/aggregation, chart construction and teardown, and the `renderChartPanel()` entry point invoked by `main.ts`. Keeps `main.ts` lean.
- `.claude/commands/e2e/test_chart_visualization.md` — New E2E test file validating the Visualize button appears, the chart renders with non-zero bar heights, axis dropdowns honor the numeric/categorical split, switching chart types works, and the button is hidden when there are zero rows.

## Implementation Plan
### Phase 1: Foundation
1. Add the `chart.js` dependency to the client with `bun add chart.js` and verify it is recorded in `app/client/package.json`. Chart.js v4 is ESM-first and works cleanly with Vite — import only the controllers / elements / plugins actually used (BarController, LineController, PieController, LineElement, BarElement, PointElement, ArcElement, CategoryScale, LinearScale, Tooltip, Legend, Title) plus `Chart.register(...)` to keep the bundle modest.
2. Create `app/client/src/chart.ts` with:
   - `type ColumnRole = 'numeric' | 'categorical'`
   - `function classifyColumns(results, columns) -> { numeric: string[]; categorical: string[] }` — A column is numeric iff (a) its name is not `id`/`rowid` (case-insensitive) and (b) at least one non-null/non-empty value in the column passes `Number.isFinite(Number(v))`. Otherwise categorical.
   - `function pickDefaults({ numeric, categorical })` — Returns `{ x: categorical[0] ?? numeric[0], y: numeric[0] }` (and `null`s when nothing is available).
   - `function toNumericSeries(results, yCol) -> { labelsIdx, values }` — coerces with `Number()` and drops rows where the value is not finite, returning the indices of the kept rows so the X labels stay aligned.
   - `function aggregatePieSlices(labels, values, max = 15)` — Sorts by value desc, keeps top `max - 1`, sums the rest into a single `"Other"` slice if there is at least one remaining; returns `{labels, values}`.
   - `function renderChartPanel(host: HTMLElement, response: QueryResponse)` — Builds the controls row, the empty-state placeholder, and the canvas; wires up listeners; performs initial render. Stores the Chart.js instance on the host element (e.g. `(host as any)._chart`) so we can `destroy()` and recreate it on every change.
3. Register only the Chart.js pieces needed at module load.

### Phase 2: Core Implementation
1. In `app/client/src/main.ts`, inside `displayResults()`:
   - After the Export button is wired up (around line 261), if `!response.error && response.results.length > 0`, create a "Visualize" button with class `visualize-button secondary-button` and insert it into the existing `buttonContainer` to the left of `exportButton`.
   - Below the `results-container`, render (or refresh) a `<div id="chart-panel" class="chart-panel">` host. The panel is appended once into `#results-section` (idempotent — check for an existing `#chart-panel` and remove or clear it before appending, the same pattern already used for `.results-header-buttons`).
   - The Visualize button toggles `chart-panel`'s display. On first click (when display goes from `none` → `block`), call `renderChartPanel(panel, response)` from `chart.ts`.
   - Every call to `displayResults()` for a new query resets the chart panel to hidden and clears any previously rendered chart instance (`destroy()` if present), since the data has changed.
2. Inside `chart.ts`'s `renderChartPanel()`:
   - Build controls: chart type `<select>` with options `Bar`, `Line`, `Pie`; X-axis `<select>` populated from `categorical`; Y-axis `<select>` populated from `numeric`.
   - If `numeric.length === 0`, render the static empty state `<div class="chart-empty">No numeric columns available</div>` and skip canvas creation.
   - Otherwise create a `<canvas>` inside a wrapper sized to `min-height: 300px; width: 100%`.
   - On any control change, call an internal `draw()` that:
     - Destroys the previous `Chart` instance if any.
     - Pulls `x` labels from the selected categorical column (raw strings, mapped through `String(v ?? '')`).
     - Pulls `y` values via `toNumericSeries()` — filtering out non-finite rows and re-aligning labels.
     - For `pie`, runs `aggregatePieSlices()` on (labels, values).
     - Builds the Chart.js config:
       - Bar / Line: `data: { labels, datasets: [{ label: yCol, data: values, backgroundColor: ..., borderColor: ... }] }`, `options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true } }, plugins: { legend: { display: true }, tooltip: { enabled: true }, title: { display: true, text: '<Y> by <X>' } } }`.
       - Pie: `data: { labels, datasets: [{ data: values, backgroundColor: <palette> }] }`, `options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: true, position: 'right' }, tooltip: { callbacks: { label: ctx => '<label>: <value> (<pct>%)' } }, title: { display: true, text: yCol } } }`.
     - Constructs `new Chart(canvas.getContext('2d')!, config)` and stores it on the host.
3. Add CSS in `app/client/src/style.css`:
   - `.chart-panel { background: var(--surface); border-radius: 12px; padding: 1.5rem; margin-top: 1rem; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }`
   - `.chart-controls { display: flex; flex-wrap: wrap; gap: 1rem; align-items: center; margin-bottom: 1rem; }`
   - `.chart-controls label { font-size: 0.9rem; color: var(--text-secondary); margin-right: 0.5rem; }`
   - `.chart-controls select { padding: 0.4rem 0.6rem; border: 1px solid var(--border-color); border-radius: 6px; background: var(--surface); }`
   - `.chart-canvas-wrapper { position: relative; width: 100%; min-height: 300px; height: 360px; }`
   - `.chart-empty { padding: 2rem; text-align: center; color: var(--text-secondary); background: var(--surface); border: 1px dashed var(--border-color); border-radius: 8px; }`
   - `.visualize-button { /* inherits .secondary-button look */ }`

### Phase 3: Integration
1. Confirm the Visualize button is hidden when `response.results.length === 0` (the surrounding `if` already guards this for Export; place the Visualize button inside the same block).
2. Confirm that running a new query rebuilds the panel from the new data and discards the previous Chart.js instance so we do not leak canvases or stale series.
3. Manually verify all three chart types render real values (especially bars are not flat / zero-height) using the sample data sets shipped with the app (`users.json`, `products.csv`, `events.jsonl`).
4. Add an E2E test (`.claude/commands/e2e/test_chart_visualization.md`) that validates the user-facing acceptance criteria and produces screenshots.
5. Run the validation commands at the end of the plan.

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

### Step 1: Read context docs
- Read `README.md`, `.claude/commands/test_e2e.md`, `.claude/commands/e2e/test_basic_query.md`, and `.claude/commands/e2e/test_export_functionality.md` to align with existing patterns.

### Step 2: Add Chart.js dependency
- `cd app/client && bun add chart.js`
- Confirm `chart.js` is present under `dependencies` in `app/client/package.json`.

### Step 3: Create the chart module
- Create `app/client/src/chart.ts`.
- Implement:
  - Top-level `Chart.register(...)` call with the controllers / elements / scales / plugins listed in Phase 1, step 2.
  - `classifyColumns(results, columns)` returning `{ numeric, categorical }`. A column is numeric iff it is not `id`/`rowid` (case-insensitive on the name) and at least one non-null/non-empty value coerces to a finite number.
  - `pickDefaults({ numeric, categorical })`.
  - `toNumericSeries(results, yCol)` — coerces with `Number()`, filters via `Number.isFinite`, returns aligned `kept` indices and numeric `values`.
  - `aggregatePieSlices(labels, values, max = 15)` — Sort, keep top `max - 1`, fold remainder into `"Other"`.
  - `renderChartPanel(host, response)` — Builds controls + canvas, wires listeners, performs initial draw. Destroys any prior chart instance stored on `host` before redrawing.
- Export `renderChartPanel`, `classifyColumns`, `pickDefaults`, and `aggregatePieSlices` (the last three are exported to keep them testable).

### Step 4: Wire the Visualize button into the results header
- Edit `app/client/src/main.ts` `displayResults()`:
  - Inside the existing `if (!response.error && response.results.length > 0)` block where Export + Hide buttons are assembled, create a third button `visualizeButton` with id `visualize-button`, class `visualize-button secondary-button`, and text `"📈 Visualize"`.
  - Insert it before `exportButton` in `buttonContainer`.
  - Create or replace a `<div id="chart-panel" class="chart-panel" style="display:none"></div>` inside `#results-section` (after `#results-container`). Guard with `document.getElementById('chart-panel')` + remove so re-displays are idempotent.
  - On Visualize click, toggle the panel display between `none` and `block`. The first time we open the panel for this query, call `renderChartPanel(panel, response)` from `chart.ts`. After that, opening again does not re-render unless the user changes selectors (which the panel handles internally).
  - When `displayResults()` is called again (new query), the existing remove-and-rebuild pattern for `.results-header-buttons` should be extended to also clear the chart panel and destroy any attached Chart.js instance.
- When `response.results.length === 0`, the Visualize button is not added at all (the existing surrounding `if` guard takes care of this).

### Step 5: Add CSS for the chart panel
- Append to `app/client/src/style.css` the rules in Phase 2 step 3 (`.chart-panel`, `.chart-controls`, `.chart-controls label`, `.chart-controls select`, `.chart-canvas-wrapper`, `.chart-empty`).
- Confirm no existing selector is overridden.

### Step 6: Verify TypeScript build is clean
- `cd app/client && bun tsc --noEmit` — fix any type errors emerging from the new module.

### Step 7: Manually exercise the feature
- `./scripts/start.sh` (or use the `start` skill).
- Load the `users`, `products`, and `events` sample data sets via the upload modal.
- Run queries that return mixed (text + numeric) columns, e.g. `Show product name and price from products`, `Show count of users by city`, `Show me all products`.
- Confirm: Visualize button appears, panel opens, defaults pick a text X and a non-`id` numeric Y, bars are non-zero height, line follows actual values, pie has proportional slices, switching chart type re-renders, the Y dropdown excludes text columns, and a 0-row result hides the button.

### Step 8: Create the E2E test
- Create `.claude/commands/e2e/test_chart_visualization.md` modeled on `test_export_functionality.md`. Cover, at minimum:
  - Load sample products data.
  - Run a query that returns at least one numeric and one text column with multiple rows (e.g. `Show product name and price from products`).
  - **Verify** a "Visualize" button appears in the results header, to the left of Export.
  - Click it; **verify** the chart panel appears with chart-type, X-axis, Y-axis selectors and a canvas of at least 300px height.
  - **Verify** the default Y axis selection is a numeric column that is NOT `id` or `rowid`.
  - **Verify** the default X axis selection is a text column.
  - **Verify** the Y-axis `<select>` has no `<option>` for text columns (e.g. product name should not appear in Y).
  - **Verify** the bar chart's tallest bar is meaningfully larger than 0 pixels (use `mcp__playwright__browser_evaluate` to read the canvas / DOM — e.g. inspect the `Chart` instance on the canvas via `(canvas as any).__chartInstance` or read computed bar coordinates; alternatively, snapshot the canvas to a screenshot and use visual judgement).
  - Switch chart type to "Pie"; **verify** the canvas re-renders.
  - Switch chart type to "Line"; **verify** the canvas re-renders.
  - Run a query with 0 rows (e.g. `SELECT * FROM products WHERE 1=0`); **verify** the Visualize button is no longer rendered.
  - Capture 4–5 screenshots and return the standard JSON output.

### Step 9: Run all validation commands
- Execute the commands in the `Validation Commands` section below in order. Fix any regressions before considering the feature complete.

## Testing Strategy
### Unit Tests
This project does not currently maintain a frontend unit test runner — pure logic checks are encoded in the E2E test plus a manual scratch check during Step 7. To keep the chart logic verifiable, ensure the pure helpers (`classifyColumns`, `pickDefaults`, `toNumericSeries`, `aggregatePieSlices`) are exported so they can be exercised from the browser console manually:

- `classifyColumns([{id:1, name:'a', price:10}], ['id','name','price'])` returns `{ numeric: ['price'], categorical: ['name'] }`.
- `pickDefaults({ numeric: ['price'], categorical: ['name'] })` returns `{ x: 'name', y: 'price' }`.
- `toNumericSeries([{p:'10'}, {p:'abc'}, {p:'20'}], 'p')` returns kept indices `[0,2]` and values `[10, 20]`.
- `aggregatePieSlices(['a','b','c','d'], [10,5,2,1], 3)` returns `{ labels: ['a','b','Other'], values: [10, 5, 3] }`.

(Server tests in `app/server` are unaffected; we still run them in validation to confirm no accidental coupling.)

### Edge Cases
- A column that contains a mix of numeric strings and free text (e.g. age column with `"30"`, `"unknown"`, `"45"`) — must be classified as numeric, and the non-numeric rows must be dropped from the series rather than treated as 0.
- All-null columns — must be classified as categorical (no finite numeric value).
- Result with only an `id` column — no numeric columns offered (since `id` is excluded), empty state shown.
- Result with only numeric columns — X-axis falls back to the first numeric column (string-cast at display time) so a chart can still be drawn.
- Result with > 15 distinct pie slice values — top 14 retained, the rest summed into "Other".
- Result with one row — bar / line chart shows a single bar / point with the correct value.
- Result with 0 rows — Visualize button is hidden entirely.
- User switches chart type without changing axes — the previous Chart.js instance is destroyed before the new one is created (no Chart.js "Canvas is already in use" error).
- User runs a new query while the chart panel is open — the panel is rebuilt from the new data and the old Chart.js instance is destroyed.
- Y values arriving as JSON numbers vs JSON strings — both are coerced via `Number()` and filtered via `Number.isFinite`; never passed as raw strings.

## Acceptance Criteria
1. The "Visualize" button is rendered in the results header to the left of "Export" whenever a query returns ≥ 1 row, and is absent when the query returns 0 rows.
2. Clicking Visualize opens a chart panel with a chart-type selector (Bar / Line / Pie), an X-axis dropdown, a Y-axis dropdown, and a canvas at least 300px tall.
3. The Y-axis dropdown only lists numeric columns (per the `classifyColumns` rule), and the X-axis dropdown only lists categorical/text columns. The user cannot select a text column for Y.
4. On first open, the X axis defaults to the first text column and the Y axis defaults to the first numeric column that is not `id` / `rowid`.
5. When the result set has no numeric columns, the panel shows the message "No numeric columns available" instead of a canvas — no empty chart is drawn.
6. Bar charts render bars with heights proportional to data values; the Y axis auto-scales with `beginAtZero: true` and Chart.js's auto-bounds.
7. Pie charts render slices proportional to values, show percentages in the tooltip, and cap at 15 slices (with overflow folded into an "Other" slice).
8. All Y-axis values are coerced via `Number()` and validated with `Number.isFinite` before being passed to Chart.js. Non-finite values are dropped, never silently coerced to 0.
9. Tooltips show the exact value on hover; the legend and axis titles are visible.
10. Switching chart type or either axis re-renders the canvas; no previous Chart.js instance leaks (no "Canvas is already in use" errors in the console).
11. `cd app/client && bun tsc --noEmit` passes with zero errors.
12. `cd app/client && bun run build` produces a successful build.
13. `cd app/server && uv run pytest` passes with zero regressions.
14. The new E2E test `test_chart_visualization.md` runs to "passed" status.

## Validation Commands
Execute every command to validate the feature works correctly with zero regressions.

- `cd app/client && bun add chart.js` — Adds the Chart.js dependency (also verify `app/client/package.json` has `chart.js` under `dependencies`).
- `cd app/client && bun tsc --noEmit` — Static type-check the client to catch any type errors in the new module / new code in `main.ts`.
- `cd app/client && bun run build` — Build the client; confirms Chart.js is bundled cleanly and no import errors slipped in.
- `cd app/server && uv run pytest` — Run server tests to confirm zero backend regressions (this should be a no-op since the change is client-only, but still required).
- Read `.claude/commands/test_e2e.md`, then read and execute the new E2E test file `.claude/commands/e2e/test_chart_visualization.md` to validate the chart-visualization functionality end-to-end (button appears, panel opens, dropdowns honor the type split, charts render non-zero values, type switching works, 0-row query hides the button).
- Read `.claude/commands/test_e2e.md`, then read and execute `.claude/commands/e2e/test_basic_query.md` to confirm the baseline query flow is not regressed by the new button / panel.
- Read `.claude/commands/test_e2e.md`, then read and execute `.claude/commands/e2e/test_export_functionality.md` to confirm the Export button still works alongside the new Visualize button.

## Notes
- New runtime dependency: `chart.js` (v4.x) — added via `cd app/client && bun add chart.js`. This is the only new dependency; we do not need `chartjs-plugin-datalabels` for percentage labels, since the percentage is included in the tooltip callback as required.
- Chart.js v4 ships as ESM and requires explicit `Chart.register(...)` for tree-shaking. The chart module registers only the controllers / elements / scales / plugins actually used, keeping the bundle reasonable.
- We deliberately keep the chart code in a new `app/client/src/chart.ts` rather than expanding `main.ts`, because `main.ts` already mixes query / upload / table / modal logic in a flat-functions style; a separate module is the smallest move that keeps the new code readable without refactoring the entire client.
- We do not introduce a frontend framework, build-step, or test runner for this feature — just plain TS + Chart.js — to match the existing codebase style.
- We do not change `types.d.ts` or any server code. The feature is client-only, as specified in the issue's `Scope` section.
- Future considerations (out of scope for this issue): persisting the user's last chart selections, exporting the chart as a PNG, supporting multiple Y series, handling time-series X axes with proper date scale.
