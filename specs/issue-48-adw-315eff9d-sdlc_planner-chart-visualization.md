# Feature: Chart Visualization

## Metadata
issue_number: `48`
adw_id: `315eff9d`
issue_json: `{"number":48,"title":"Chart Visualization","body":"/feature\n\nadw_sdlc_iso\n\nmodel_set heavy\n\nAfter a query returns results, show a \"Visualize\" button. Renders data as a bar, line, or pie chart using Chart.js. User picks chart type and which columns to use for axes. The chart must display actual data values -- not empty charts, flat lines, or zero-height bars.\n\n**Scope:**\n- Client-only change -- add Chart.js dependency, chart type selector, axis dropdowns\n- Renders from the same data already in the results table\n\n**Acceptance criteria:**\n1. Y-axis dropdown only offers numeric columns; X-axis dropdown only offers categorical/text columns -- never allow non-numeric data on the Y-axis (it renders as zeros)\n2. Auto-select sensible defaults: first text column for X, first numeric column (excluding id/rowid) for Y\n3. If no numeric columns exist, show \"No numeric columns available\" instead of an empty chart\n4. Bar chart bars have heights proportional to data values; Y-axis auto-scales to fit the data\n5. Pie chart slices are proportional to values with percentage labels; max 15 slices (remainder grouped as \"Other\")\n6. All Y-axis values are parsed as numbers before charting -- never pass raw strings to Chart.js\n7. Tooltips show exact values on hover; legend and axis labels are visible\n8. Chart has minimum 300px height and is readable without scrolling\n9. If results table has 0 rows, the Visualize button is hidden"}`

## Feature Description
Add a client-side data visualization feature to the Natural Language SQL Interface. After a query returns one or more rows of results, a **Visualize** button appears alongside the existing Export/Hide buttons in the results header. Clicking it reveals a chart panel that renders the current query results as a **bar**, **line**, or **pie** chart using [Chart.js](https://www.chartjs.org/).

The user chooses the chart type from a selector and picks which columns to use for the axes via two dropdowns (X-axis and Y-axis). The Y-axis dropdown only lists numeric columns, and the X-axis dropdown only lists categorical/text columns, which guarantees the chart always displays real, proportional data values rather than empty charts, flat lines, or zero-height bars.

All data used for the chart comes from the same `response.results` / `response.columns` data already displayed in the results table — this is a purely client-only change with no server modifications.

## User Story
As a user of the Natural Language SQL Interface
I want to visualize my query results as bar, line, or pie charts
So that I can quickly understand trends and comparisons in my data without exporting it to another tool

## Problem Statement
Query results are currently only displayed as a raw HTML table. Tabular data is hard to interpret at a glance — users cannot easily spot trends, compare magnitudes, or understand distributions. There is no built-in way to visualize the data, forcing users to export the results and use an external tool. Additionally, naive charting implementations frequently produce broken visuals (empty charts, flat lines, zero-height bars) when non-numeric strings are passed to the charting library or when inappropriate columns are chosen for the axes.

## Solution Statement
Introduce a client-only chart visualization module that:
1. Adds a **Visualize** button to the results header (only when there is at least one result row).
2. Renders an inline chart panel containing a chart-type selector (bar/line/pie), an X-axis dropdown, a Y-axis dropdown, and a `<canvas>` element for Chart.js.
3. Classifies columns into numeric vs. categorical by inspecting the actual result values, so the Y-axis dropdown only offers numeric columns and the X-axis dropdown only offers text/categorical columns.
4. Auto-selects sensible defaults (first text column for X, first non-`id`/`rowid` numeric column for Y).
5. Coerces every Y-axis value to a number (`Number(...)`, filtering out `NaN`) before passing it to Chart.js, guaranteeing proportional, auto-scaled charts.
6. Handles edge cases gracefully: no numeric columns → "No numeric columns available" message; zero rows → the Visualize button is hidden entirely; pie charts with more than 15 categories group the remainder into an "Other" slice.

Chart.js is added as a client dependency via Bun. All logic lives in the existing Vite + TypeScript client (`app/client/src`), following the current pattern of DOM manipulation in `main.ts`.

## Relevant Files
Use these files to implement the feature:

- `app/client/src/main.ts` - Main client logic. Contains `displayResults()` (where the results header buttons are built, ~line 189-262), `createResultsTable()`, and all DOM rendering. The Visualize button and chart panel wiring will be added here, following the existing export-button pattern.
- `app/client/index.html` - Static HTML shell. The results section (`#results-section`, `.results-header`, `#results-container`) lives here. A chart container element may be added here (or created dynamically in `main.ts`).
- `app/client/src/style.css` - All application styles. New styles for the chart panel, chart controls (selector + dropdowns), and the Visualize button will be added here, reusing the existing `.secondary-button`, `.results-header-buttons` conventions. **Read this file before making style changes** (per `.claude/commands/conditional_docs.md`).
- `app/client/src/types.d.ts` - Global TypeScript interfaces (e.g. `QueryResponse` with `results`/`columns`). Any new chart-related types (e.g. a column-classification type or chart config type) go here.
- `app/client/package.json` - Client dependency manifest. Chart.js will be added here via `bun add chart.js`.
- `app/client/tsconfig.json` - TypeScript compiler config; verify Chart.js types resolve for `bun tsc --noEmit`.
- `README.md` - Project overview and commands. **Read first** to understand project structure and how to start/build the client (per `.claude/commands/conditional_docs.md`).
- `.claude/commands/test_e2e.md` - **Read this** to understand how the E2E test runner executes test files (setup, screenshots, output format).
- `.claude/commands/e2e/test_basic_query.md` - **Read this** as the reference example for writing a new E2E test file (structure: User Story, Test Steps, Success Criteria).
- `.claude/commands/e2e/test_export_functionality.md` - Additional E2E reference; the Visualize button lives next to the Export button, so this test shows the closest existing UI-interaction pattern.

### New Files
- `app/client/src/chart.ts` - New module encapsulating all chart-visualization logic: column classification (numeric vs. categorical), default axis selection, data coercion, Chart.js instance lifecycle (create/destroy on re-render), pie-slice grouping ("Other"), and building the chart controls UI. Keeps `main.ts` focused and the feature testable. (Simple functions only — no classes/decorators.)
- `.claude/commands/e2e/test_chart_visualization.md` - New E2E test file validating the chart visualization feature end-to-end (following `test_basic_query.md` conventions).

## Implementation Plan
### Phase 1: Foundation
- Add the Chart.js dependency to the client via `bun add chart.js` (run inside `app/client`).
- Verify Chart.js ships its own TypeScript types (it does, bundled) so `bun tsc --noEmit` resolves imports.
- Create the `app/client/src/chart.ts` module scaffold with pure helper functions for column classification and value coercion.

### Phase 2: Core Implementation
- Implement column classification in `chart.ts`: given `results` and `columns`, determine which columns are numeric (values coerce to finite numbers for the majority of non-null rows) and which are categorical/text.
- Implement default axis selection: first text column for X; first numeric column excluding `id`/`rowid` (case-insensitive) for Y.
- Implement `renderChart()`: reads current chart type + selected X/Y columns, coerces Y values with `Number(...)`, filters `NaN`, aggregates as needed, groups pie slices beyond 15 into "Other", destroys any prior Chart.js instance, and creates a new one with a min-300px-height canvas, visible legend, axis labels, and tooltips showing exact values.
- Implement `buildChartControls()`: creates the chart-type selector (bar/line/pie), the X-axis dropdown (categorical columns only), the Y-axis dropdown (numeric columns only), and wires change handlers to re-render.
- Handle the "no numeric columns" edge case: render a "No numeric columns available" message instead of the chart/controls.

### Phase 3: Integration
- In `main.ts` `displayResults()`, add a **Visualize** button to the `.results-header-buttons` container, but only when `response.results.length > 0` (so it is hidden for zero-row results).
- Clicking **Visualize** toggles a chart panel (created via `chart.ts`) below the results table, populated from `response.results` / `response.columns`.
- Ensure the chart panel and any existing Chart.js instance are properly reset/destroyed when a new query runs (avoid stale charts / canvas reuse errors).
- Add styles in `style.css` for the chart panel, controls row, and Visualize button.
- Create the E2E test file and validate.

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

### Task 1: Read reference documentation
- Read `README.md` to confirm client structure and build/start commands.
- Read `app/client/src/style.css` (conditional doc for style changes).
- Read `.claude/commands/test_e2e.md` and `.claude/commands/e2e/test_basic_query.md` and `.claude/commands/e2e/test_export_functionality.md` to understand E2E test structure before writing the new test.

### Task 2: Add the Chart.js dependency
- From `app/client`, run `bun add chart.js`.
- Confirm `chart.js` appears in `app/client/package.json` dependencies and that `bun install` succeeded.
- Report the new dependency in the Notes section.

### Task 3: Create the chart module (`app/client/src/chart.ts`)
- Add a helper `classifyColumns(results, columns)` returning `{ numeric: string[]; categorical: string[] }`.
  - A column is **numeric** if, across non-null values, the majority coerce to a finite number via `Number(v)` (guard empty strings → not numeric).
  - All other columns (including numeric-but-mostly-null) are **categorical**.
- Add `pickDefaultAxes(numeric, categorical)`:
  - X default = first categorical column (fallback: first column).
  - Y default = first numeric column whose lowercased name is not `id` or `rowid`; fallback to first numeric column.
- Add `coerceNumeric(value): number | null` returning `Number(value)` if finite, else `null`.
- Add `buildChartData(results, xCol, yCol, chartType)`:
  - Extracts labels from `xCol` (as strings) and values from `yCol` via `coerceNumeric`, dropping rows where the Y value is `null`.
  - For **pie** charts: if more than 15 categories, keep the top 15 by value and sum the rest into an "Other" slice.
- Add `renderChart(canvas, results, xCol, yCol, chartType, prevChart)`:
  - Destroys `prevChart` if present (prevents Chart.js "Canvas is already in use" errors).
  - Creates a new `Chart` instance with:
    - `type` = `bar` | `line` | `pie`.
    - Data from `buildChartData`.
    - `responsive: true`, `maintainAspectRatio: false` (canvas container enforces min 300px height).
    - Y-axis `beginAtZero: true` for bar/line so bars auto-scale from zero (bar/line only; pie has no axes).
    - Legend visible; axis titles set to the selected column names (bar/line).
    - Tooltip callbacks showing the exact Y value; for pie, tooltip/labels show value + percentage of total.
  - Returns the new `Chart` instance.
- Add `buildChartControls(container, results, columns, onChange)`:
  - Classifies columns; if `numeric` is empty, render a `<div class="chart-empty">No numeric columns available</div>` and return without controls.
  - Otherwise build: a chart-type `<select>` (Bar/Line/Pie), an X-axis `<select>` populated with categorical columns, a Y-axis `<select>` populated with numeric columns, defaults applied via `pickDefaultAxes`.
  - Wire `change` events on all three selects to call `onChange(chartType, xCol, yCol)`.
- Keep all exports as plain functions (no classes, no decorators).

### Task 4: Add chart-related types to `types.d.ts`
- Add a `ColumnClassification` interface (`{ numeric: string[]; categorical: string[] }`) and a `ChartType` union (`'bar' | 'line' | 'pie'`) if useful for typing the module. Keep minimal.

### Task 5: Integrate the Visualize button + chart panel in `main.ts`
- In `displayResults()`, inside the existing `if (!response.error && response.results.length > 0)` block that builds `results-header-buttons`:
  - Create a **Visualize** button (`class="visualize-button secondary-button"`, title "Visualize results as a chart") and append it to `buttonContainer` before the toggle button.
  - Because this block only runs when `results.length > 0`, the Visualize button is inherently hidden for zero-row results (acceptance criterion 9). Do not add it in the zero-row / error branches.
- Add a chart panel container element under the results container (create dynamically in `main.ts`, or add a `<div id="chart-container" class="chart-container" style="display:none">` in `index.html`).
- Clicking **Visualize** toggles the chart panel visibility. On first open (or whenever a new query is displayed), call `buildChartControls(...)` and render the initial chart from defaults via `renderChart(...)`.
- Maintain a module-level reference to the active `Chart` instance so it can be destroyed before re-rendering and before displaying a new query's results (reset on each `displayResults`).
- Ensure that when a new query result is displayed, any previously-open chart panel and its Chart.js instance are cleared/destroyed to avoid stale visuals.

### Task 6: Add styles in `style.css`
- Add `.visualize-button` styling (reuse/inherit `.secondary-button` look; match the existing `.export-button` sizing).
- Add `.chart-container` styling: block layout, top margin, padding, border/background consistent with the results section.
- Add `.chart-controls` styling: a flex row of the type selector + axis dropdowns with labels, wrapping on small screens.
- Add `.chart-canvas-wrapper` with `min-height: 300px` and `position: relative` so Chart.js `maintainAspectRatio:false` fills it and the chart is readable without scrolling (acceptance criterion 8).
- Add `.chart-empty` message styling.

### Task 7: Create the E2E test file
- Create `.claude/commands/e2e/test_chart_visualization.md` following the structure of `test_basic_query.md`.
- Test steps (minimal set to prove the feature):
  1. Navigate to the Application URL; screenshot initial state.
  2. Load sample data (e.g. Product Inventory sample, which has numeric price/quantity columns) via the Upload modal → sample button, OR run a query against an existing table with numeric columns.
  3. Enter a query that returns rows with both a text/categorical column and a numeric column (e.g. "Show me all products with their prices").
  4. Click Query; **Verify** results table shows data; screenshot.
  5. **Verify** the **Visualize** button is present in the results header.
  6. Click **Visualize**; **Verify** the chart panel appears with a chart-type selector, X-axis dropdown, and Y-axis dropdown; screenshot the rendered bar chart.
  7. **Verify** the Y-axis dropdown contains only numeric columns and the X-axis dropdown contains only text columns.
  8. **Verify** the chart canvas renders a non-empty chart (bars have height / not all zero) — inspect via a screenshot showing visible bars.
  9. Switch chart type to Pie; **Verify** slices render; screenshot.
  10. (Edge case) Optionally verify that a query returning zero rows does NOT show the Visualize button.
- Include Success Criteria mirroring the acceptance criteria (button appears only with rows, dropdowns are correctly filtered, chart renders real values, at least 3 screenshots taken).

### Task 8: Run all validation commands
- Run every command in the **Validation Commands** section and fix any failures until all pass with zero regressions.

## Testing Strategy
### Unit Tests
The client has no existing JS/TS unit-test harness (validation is via `tsc --noEmit`, `bun run build`, and E2E). Therefore:
- Primary validation for the pure helper functions (`classifyColumns`, `pickDefaultAxes`, `coerceNumeric`, `buildChartData` "Other" grouping) is TypeScript type-checking (`bun tsc --noEmit`) plus the end-to-end behavior exercised by the E2E test.
- Keep the helper functions pure and side-effect-free so their behavior is deterministic and observable through the E2E test.
- Server-side `uv run pytest` must continue to pass (this is a client-only change; it should be an unaffected regression check).

### Edge Cases
- **Zero result rows** → Visualize button hidden entirely (criterion 9).
- **No numeric columns** in results → "No numeric columns available" message instead of a chart (criterion 3).
- **Y-axis values stored as strings** (e.g. `"42"`) → coerced with `Number(...)` so bars/lines are proportional, not zero (criteria 4, 6).
- **Non-numeric strings never selectable for Y-axis** (dropdown filtered) — prevents zero-height/flat charts (criterion 1).
- **`id` / `rowid` columns** excluded from the default Y selection (criterion 2).
- **Pie chart with > 15 categories** → top 15 kept, remainder summed into "Other" (criterion 5).
- **Re-running a query while a chart is open** → prior Chart.js instance destroyed, no "canvas already in use" error, no stale data.
- **Null / missing Y values** → rows dropped from the dataset, not charted as zero.
- **Switching chart type** (bar ↔ line ↔ pie) re-renders correctly with the same selected columns.

## Acceptance Criteria
1. The Y-axis dropdown lists only numeric columns; the X-axis dropdown lists only categorical/text columns. Non-numeric data can never be selected for the Y-axis.
2. On opening the chart panel, defaults auto-select the first text column for X and the first numeric column (excluding `id`/`rowid`) for Y.
3. When the result set has no numeric columns, the panel shows "No numeric columns available" instead of an empty chart.
4. Bar charts render bars with heights proportional to the underlying values, and the Y-axis auto-scales to fit the data (begins at zero).
5. Pie charts render slices proportional to values with percentage labels; when there are more than 15 categories, the remainder is grouped into a single "Other" slice (max 15 + Other).
6. Every Y-axis value is parsed to a number (`Number(...)`, `NaN` filtered) before being passed to Chart.js — no raw strings reach the chart.
7. Hovering a data point shows a tooltip with the exact value; the legend and axis labels are visible.
8. The chart has a minimum height of 300px and is readable without scrolling.
9. When the results table has 0 rows, the Visualize button is not shown.
10. The change is client-only (no server code modified); the chart renders from the same data already in the results table.
11. All validation commands pass with zero regressions.

## Validation Commands
Execute every command to validate the feature works correctly with zero regressions.

- `cd app/client && bun install` - Ensure the new Chart.js dependency is installed.
- `cd app/client && bun tsc --noEmit` - Type-check the client (chart.ts, main.ts, types.d.ts) with zero errors.
- `cd app/client && bun run build` - Build the client for production with zero errors.
- `cd app/server && uv run pytest` - Run server tests to confirm zero regressions (client-only change must not break the server).
- Read `.claude/commands/test_e2e.md`, then read and execute the new E2E test file `.claude/commands/e2e/test_chart_visualization.md` to validate the chart visualization works end-to-end (Visualize button appears, dropdowns are correctly filtered, bar and pie charts render real, non-zero data values, screenshots captured).

## Notes
- **New dependency:** `chart.js` (added to `app/client/package.json` via `bun add chart.js`). Chart.js bundles its own TypeScript type definitions, so no separate `@types/chart.js` package is needed. Report this dependency addition when implementing.
- Use Chart.js `auto`/tree-shakeable import as convenient; the simplest reliable approach is `import Chart from 'chart.js/auto'` which registers all controllers/scales automatically (bar, line, pie) — appropriate here since we support all three types.
- This is intentionally a **client-only** change per the issue scope; do not add or modify any server endpoints or Python code.
- Keep the implementation simple and function-based (no classes, no decorators), consistent with the existing `main.ts` style.
- Chart.js requires destroying the previous chart instance before re-rendering on the same canvas — track the active instance at module scope in the chart integration to avoid "Canvas is already in use" runtime errors.
- The Product Inventory sample dataset (`products.csv`, prices + quantities) is a good, reliable dataset for the E2E test because it contains both categorical (product name/category) and numeric (price/quantity) columns.
