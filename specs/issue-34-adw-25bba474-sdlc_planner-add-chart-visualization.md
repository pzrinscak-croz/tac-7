# Feature: Chart Visualization for Query Results

## Metadata
issue_number: `34`
adw_id: `25bba474`
issue_json: `{"number":34,"title":"Chart Visualization","body":"/feature\n\nadw_sdlc_iso\n\nmodel_set heavy\n\nAfter a query returns results, show a \"Visualize\" button. Renders data as a bar, line, or pie chart using Chart.js. User picks chart type and which columns to use for axes. The chart must display actual data values -- not empty charts, flat lines, or zero-height bars.\n\n**Scope:**\n- Client-only change -- add Chart.js dependency, chart type selector, axis dropdowns\n- Renders from the same data already in the results table\n\n**Acceptance criteria:**\n1. Y-axis dropdown only offers numeric columns; X-axis dropdown only offers categorical/text columns -- never allow non-numeric data on the Y-axis (it renders as zeros)\n2. Auto-select sensible defaults: first text column for X, first numeric column (excluding `id`/`rowid`) for Y\n3. If no numeric columns exist, show \"No numeric columns available\" instead of an empty chart\n4. Bar chart bars have heights proportional to data values; Y-axis auto-scales to fit the data\n5. Pie chart slices are proportional to values with percentage labels; max 15 slices (remainder grouped as \"Other\")\n6. All Y-axis values are parsed as numbers before charting -- never pass raw strings to Chart.js\n7. Tooltips show exact values on hover; legend and axis labels are visible\n8. Chart has minimum 300px height and is readable without scrolling\n9. If results table has 0 rows, the Visualize button is hidden"}`

## Feature Description
Add an interactive chart visualization capability to the Natural Language SQL Interface. After a query returns non-empty results, a new "Visualize" button appears alongside the existing Export and Hide buttons. Clicking it opens a chart panel inside the results section where the user picks the chart type (bar, line, or pie) and selects which columns to use for the X and Y axes. The chart renders using Chart.js from the data already loaded in the results table — there is no additional API request. The implementation must produce charts that show real, proportional data — not empty canvases, flat lines, or zero-height bars — by detecting numeric vs. categorical columns from the result rows and coercing all Y-axis values to numbers before passing them to Chart.js.

## User Story
As a data analyst using the Natural Language SQL Interface
I want to visualize query results as bar, line, or pie charts directly in the browser
So that I can quickly spot trends, comparisons, and distributions in my data without exporting to a separate tool.

## Problem Statement
Today, the only way to inspect query output is the tabular results display. Tables are fine for lookups but make it hard to see relative magnitudes, trends, or distributions across many rows. Users also cannot share a quick visual summary of a result without copying data into Excel, Google Sheets, or another tool. The bar of effort for "I just want to see this as a chart" is too high.

A naive implementation of charting would also misbehave on this app's data: query results frequently contain mixed types (text columns like `name`, numeric columns like `price`, and ID columns like `id` or `rowid`). If any non-numeric column is selected for the Y-axis, Chart.js silently renders zeros, producing empty/flat charts. The feature must defend against this.

## Solution Statement
Add a client-only chart visualization panel to the results section.

1. Add Chart.js as a runtime dependency (`bun add chart.js`).
2. After every successful, non-empty query, render a "Visualize" button next to the existing Export/Hide buttons. Hide the button when results are empty.
3. Clicking Visualize toggles a visualization panel below the SQL display containing:
   - A chart type selector (bar / line / pie) implemented as a segmented button group.
   - X-axis and Y-axis `<select>` dropdowns populated with the columns from the current result set.
   - A `<canvas>` element where Chart.js renders the chart.
4. Detect column types from the row data on the client (no backend changes): a column is "numeric" if every non-null value coerces cleanly to a finite number; otherwise it is "categorical/text".
5. The Y-axis dropdown is restricted to numeric columns only (excluding `id` and `rowid` from auto-selection but allowed if the user picks them). The X-axis dropdown is restricted to categorical/text columns (with a fallback to all columns if none qualify).
6. If no numeric columns exist, the chart area shows "No numeric columns available" and the chart is not rendered.
7. For bar/line charts, the chart re-renders whenever the user changes type, X column, or Y column. Y values pass through `Number()` and a finite check before being plotted.
8. For pie charts, slices are proportional to Y values; if the result set has more than 15 categories, the top 14 by value are kept and the rest are aggregated into a single "Other" slice. Tooltips show absolute value and percentage.
9. The `<canvas>` is wrapped in a container with `min-height: 300px` so the chart is always readable without scrolling. Chart.js is configured with `responsive: true`, `maintainAspectRatio: false`, visible axis labels, tooltips, and legend.

This is a fully client-side feature — no API or schema changes — keeping blast radius small.

## Relevant Files
Use these files to implement the feature:

- `app/client/index.html` — Contains the HTML structure for the results section. We will add a hidden visualization panel (chart type selector, axis dropdowns, canvas) inside `#results-section` so the layout is co-located with the results.
- `app/client/src/main.ts` — Owns the existing `displayResults`, button rendering, and DOM wiring. We will add: `getDownloadIcon`-style helpers for chart UI, a new `initializeVisualization(results, columns)` function, column-type detection helpers (`isNumericColumn`, `getColumnTypes`), and integration into `displayResults` so the Visualize button shows on non-empty results.
- `app/client/src/types.d.ts` — Declares `QueryResponse`, `columns`, etc. We may add a small type for chart configuration state (chart type union, selected axes) here.
- `app/client/src/style.css` — Contains existing button/section styling. We will add styles for the visualization panel: `.visualize-button`, `.visualization-panel`, `.chart-type-selector`, `.axis-controls`, and `.chart-container { min-height: 300px }`.
- `app/client/package.json` — Will gain the `chart.js` runtime dependency via `bun add chart.js`.
- `app/client/src/api/client.ts` — Read-only reference; confirms no backend API changes are needed (the existing query response already contains `results` and `columns`).
- `README.md` — Client-side feature list mentions "Interactive table results display"; we will append a brief mention of chart visualization.
- `.claude/commands/test_e2e.md` — Read this before authoring the new E2E test file. Describes how Playwright-based E2E tests are run, screenshot conventions, and the JSON output format.
- `.claude/commands/e2e/test_basic_query.md` — Reference example of an E2E test for query execution. Use it as a structural template (User Story → Test Steps → Success Criteria) for the new chart visualization E2E test.
- `.claude/commands/e2e/test_export_functionality.md` — Reference example of an E2E test that interacts with buttons added next to results (Export/Hide). The new chart test follows a very similar pattern (button placement, file upload + query setup, screenshots).

### New Files
- `specs/issue-34-adw-25bba474-sdlc_planner-add-chart-visualization.md` — This plan file (already being created).
- `.claude/commands/e2e/test_chart_visualization.md` — New E2E test that uploads sample data, runs a query, clicks Visualize, switches chart types, changes axis selections, and verifies the chart renders with non-empty data. Must follow the same `User Story` / `Test Steps` / `Success Criteria` format as the other tests in `.claude/commands/e2e/`.

## Implementation Plan

### Phase 1: Foundation
- Install `chart.js` as a runtime dependency in `app/client/`.
- Add the visualization panel skeleton (hidden by default) to `app/client/index.html` inside the results section.
- Add CSS for the visualization panel, chart-type selector pill group, axis controls row, and chart container with a 300px minimum height.
- Add a small `Chart` import and a single `currentChart: Chart | null` module-level variable in `main.ts` so the chart instance can be destroyed and re-created cleanly when inputs change.

### Phase 2: Core Implementation
- Add column-type detection helpers in `main.ts`:
  - `isNumericValue(v: any): boolean` — returns true for finite numbers and numeric strings (excluding empty string).
  - `isNumericColumn(results: Record<string, any>[], col: string): boolean` — returns true if every non-null value in the column is numeric and the column has at least one non-null value.
  - `getColumnTypes(results, columns)` — returns `{ numeric: string[], categorical: string[] }`.
- Add `initializeVisualization(results, columns)`:
  - Determine numeric and categorical columns.
  - If `numeric.length === 0`, show the "No numeric columns available" message inside the panel and skip chart rendering.
  - Populate axis dropdowns: X gets categorical (or all columns as fallback), Y gets numeric only.
  - Apply default selections: first non-`id`/`rowid` text column for X (fallback to first column), first numeric column whose name is not `id` or `rowid` (fallback to first numeric).
  - Wire change handlers on chart type and axis selects to call `renderChart()`.
- Add `renderChart(results, type, xCol, yCol)`:
  - Destroy any previous `currentChart` instance.
  - Coerce Y values via `Number(...)` and filter out non-finite values; X values are stringified.
  - For pie: compute totals per X label, sort descending, keep top 14, group remainder into a single `"Other"` slice if more than 15 categories. Configure tooltip callbacks to display value and percentage.
  - For bar/line: build `labels` (X values) and `data` (numeric Y values). Use Chart.js options with `responsive: true`, `maintainAspectRatio: false`, visible axis titles (`scales.x.title.text` = X column name, `scales.y.title.text` = Y column name), `scales.y.beginAtZero: true`, and a tooltip showing exact values.
- Wire the Visualize button into `displayResults`:
  - In the existing `if (!response.error && response.results.length > 0)` branch, prepend a Visualize button to the `.results-header-buttons` container (left of Export and Hide).
  - Clicking it toggles the visualization panel's visibility and calls `initializeVisualization` on first open.
  - When results are empty or errored, ensure the Visualize button and any prior visualization panel are removed (or hidden) so the rule "If results table has 0 rows, the Visualize button is hidden" holds.

### Phase 3: Integration
- Confirm no regressions to existing features: query execution, Export button (CSV), Hide/Show toggle, table upload, sample data, random query generation.
- Update README.md feature bullet list to mention chart visualization.
- Run TypeScript build and ensure no type errors.
- Run the new E2E test and existing E2E tests (basic query, export functionality) to confirm zero regressions.

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

### Step 1: Read conditional documentation
- Read `README.md` (client/server overview).
- Read `.claude/commands/test_e2e.md` (E2E runner conventions).
- Read `.claude/commands/e2e/test_basic_query.md` and `.claude/commands/e2e/test_export_functionality.md` (E2E test format references).
- Read `app/client/src/style.css` (since this task changes client styles, per `conditional_docs.md`).

### Step 2: Add Chart.js dependency
- In `app/client/`, run `bun add chart.js` to add it to `package.json` and `bun.lock`.
- Verify `package.json` now lists `chart.js` under `dependencies`.

### Step 3: Add visualization panel HTML scaffold
- Edit `app/client/index.html`. Inside `#results-section`, after `#results-container`, add a new hidden `<section id="visualization-panel" class="visualization-panel" style="display: none;">` containing:
  - A chart-type selector with three buttons (`data-chart-type="bar|line|pie"`), bar selected by default.
  - Two `<select>` elements for X-axis and Y-axis with labels.
  - A `<div class="chart-container">` wrapping a `<canvas id="chart-canvas">`.
  - A `<div id="chart-empty-state" class="chart-empty-state" style="display: none;">` for the "No numeric columns available" message.

### Step 4: Add CSS for visualization panel
- Edit `app/client/src/style.css`. Add styles for:
  - `.visualization-panel` (matches `.sql-display`/`.results-container` padding and spacing).
  - `.visualize-button` (reuses `.export-button` look or adds a complementary style).
  - `.chart-type-selector` (segmented pill group; active state highlighted).
  - `.axis-controls` (flex row with two labeled selects, gap, wraps on narrow screens).
  - `.chart-container { position: relative; min-height: 300px; }` so Chart.js responsive sizing works.
  - `.chart-empty-state` (centered grey text, matching the existing "no results" tone).

### Step 5: Add column-type detection helpers in main.ts
- In `app/client/src/main.ts`, add the helper functions `isNumericValue`, `isNumericColumn`, and `getColumnTypes` near the existing helper section.
- A column is numeric only if it has at least one non-null value AND every non-null value passes `isNumericValue`.

### Step 6: Add chart rendering logic in main.ts
- Import `Chart` and the chart types/elements you need from `chart.js/auto` (the `auto` entrypoint registers all controllers; this avoids manual registration).
- Add a module-scoped `let currentChart: Chart | null = null;`.
- Add `renderChart(results, type, xCol, yCol)`:
  - Destroy `currentChart` if present.
  - Build numeric Y series (coerce via `Number`, filter non-finite).
  - For pie, aggregate by X, sort, top-14 + "Other" if >15 categories.
  - Construct the Chart.js config and assign the new instance to `currentChart`.
  - Configure responsive, no-aspect-ratio-lock, axis titles, legend, and tooltips.

### Step 7: Add visualization initializer and Visualize button wiring
- Add `initializeVisualization(results, columns)` to populate axis dropdowns based on numeric/categorical detection, apply defaults (skipping `id`/`rowid` for Y when alternatives exist), wire change handlers to call `renderChart`, and call `renderChart` once on open.
- In `displayResults`, when results are non-empty and no error:
  - Create a `Visualize` button and prepend it to `.results-header-buttons` (left of Export and Hide).
  - On first click, call `initializeVisualization`. Subsequent clicks toggle the panel's `display` between `block` and `none`. Update button text/state accordingly (e.g., "Visualize" / "Hide Chart" or aria-pressed toggle).
  - When results are empty or error is present, ensure no Visualize button is shown and the panel is hidden / chart destroyed.

### Step 8: Handle the "no numeric columns" empty state
- If `getColumnTypes(...).numeric.length === 0`, show `#chart-empty-state` with text "No numeric columns available" and hide the chart canvas + axis controls.
- Otherwise, show the controls + canvas and hide the empty state.

### Step 9: Author the new E2E test file
- Create `.claude/commands/e2e/test_chart_visualization.md` following the same structure as `test_basic_query.md` and `test_export_functionality.md`.
- Test steps (minimal but proves the feature works):
  1. Navigate to Application URL; verify page title.
  2. Open Upload modal and click the "Product Inventory" sample button (products.csv has both text and numeric columns — `name`, `category`, `price`, `quantity`).
  3. Run query: "Show me all products" (or `SELECT * FROM products LIMIT 10`).
  4. Verify results table appears.
  5. Verify the Visualize button is present in the results header buttons.
  6. Click Visualize; verify the visualization panel appears with chart-type selector, X/Y dropdowns, and a canvas.
  7. Verify Y-axis dropdown contains a numeric column (e.g., `price`) and not a pure text column (e.g., `name`).
  8. Take a screenshot of the bar chart.
  9. Switch chart type to "line"; verify the chart re-renders. Take a screenshot.
  10. Switch chart type to "pie"; verify the chart re-renders. Take a screenshot.
  11. Verify (via Playwright DOM inspection or evaluate) that the canvas element exists and has non-zero width/height — proving the chart is laid out and rendered.
  12. Run a new query that returns 0 rows ("SELECT * FROM products WHERE 1=0"); verify the Visualize button is hidden.
  13. Take a final screenshot.

### Step 10: Update README
- In `README.md`, append a feature bullet under `## Features` such as: "📈 Chart visualization (bar / line / pie) of query results using Chart.js".

### Step 11: Run validation commands
- Execute every command in the `Validation Commands` section. Fix any TypeScript, lint, build, or test errors before considering the task complete.

## Testing Strategy

### Unit Tests
This is a client-only feature in a TypeScript codebase that does not currently have a frontend unit test setup. Validation is therefore performed via:
- TypeScript type checking (`bun tsc --noEmit`).
- Production build (`bun run build`) to catch any bundling issues with the new Chart.js import.
- Server tests (`uv run pytest`) to confirm the backend was not affected.
- An E2E Playwright test that exercises the full UI flow.

If reviewers feel a unit test layer is warranted, the column-type detection helpers (`isNumericValue`, `isNumericColumn`, `getColumnTypes`) are pure functions and would be the right place to start; that is out of scope for this issue.

### Edge Cases
- Empty result set (0 rows): Visualize button hidden.
- Single-row result set: chart renders with one bar/slice.
- All-numeric result set with no text columns: X-axis falls back to all columns (so user can still pick something like `id`).
- Result set with only an `id`-like numeric column: numeric Y is `id` (allowed when nothing else qualifies); X falls back to the same set; chart renders without crashing.
- No numeric columns at all (e.g., all text): empty state "No numeric columns available" is shown and Chart.js is not invoked.
- Mixed-type column where some rows are numeric strings and some are text: classified as non-numeric (categorical), so it does not appear on Y axis.
- Null values in the Y column: filtered out before rendering, the corresponding row is skipped (not plotted as zero).
- Pie chart with > 15 categories: top 14 retained, remainder grouped into a single "Other" slice with summed value.
- Switching chart type repeatedly: previous Chart.js instance is destroyed each time to avoid the "Canvas is already in use" Chart.js error.
- Running a new query while the panel is open: previous chart is destroyed, panel state is reset to defaults for the new column set.
- Long column names: select dropdowns show full text; chart axis titles wrap or truncate gracefully via Chart.js defaults.

## Acceptance Criteria
1. `chart.js` is added as a dependency in `app/client/package.json` and lockfile.
2. After a successful query that returns ≥ 1 row, a "Visualize" button is visible in the results header alongside Export and Hide.
3. After a query that returns 0 rows (or errors), the Visualize button is not rendered.
4. Clicking Visualize reveals a panel containing: a chart-type selector (bar/line/pie), X-axis select, Y-axis select, and a chart canvas.
5. The Y-axis select offers only numeric columns. Picking any provided option results in a chart with non-zero, proportional values.
6. The X-axis select offers only categorical/text columns (with a documented fallback to all columns if none qualify).
7. Defaults: X = first non-id text column (fallback to first column); Y = first numeric column whose name is not `id`/`rowid` (fallback to first numeric column).
8. If the result set has no numeric columns, the panel shows "No numeric columns available" and no chart is rendered.
9. Bar charts have bars whose pixel heights are proportional to their data values (Y axis auto-scales, beginAtZero true).
10. Line charts plot a polyline through the data points; the line is not flat at zero.
11. Pie charts have slices proportional to values; tooltip shows the absolute value and percentage; if more than 15 categories exist, the chart shows at most 15 slices with a single "Other" aggregating the remainder.
12. All Y values are coerced via `Number(...)` (and finite-checked) before being passed to Chart.js — no raw strings reach the chart dataset.
13. Chart tooltips display exact values on hover; the legend and X/Y axis titles (using the column names) are visible.
14. The chart container has `min-height: 300px` and the chart is readable without horizontal or vertical scrolling at the default viewport.
15. Changing the chart type, X column, or Y column re-renders the chart correctly (no leaked Chart.js instances, no "canvas already in use" errors).
16. `cd app/server && uv run pytest` passes with zero failures.
17. `cd app/client && bun tsc --noEmit` reports no type errors.
18. `cd app/client && bun run build` completes successfully.
19. The new E2E test `.claude/commands/e2e/test_chart_visualization.md` runs and reports `status: "passed"`.

## Validation Commands
Execute every command to validate the feature works correctly with zero regressions.

- `cd app/client && bun install` — Ensure the new `chart.js` dependency is installed.
- `cd app/server && uv run pytest` — Run backend tests; must pass with zero failures (no backend changes expected, this confirms zero regressions).
- `cd app/client && bun tsc --noEmit` — TypeScript type-check; must report no errors.
- `cd app/client && bun run build` — Production build; must succeed without errors.
- Read `.claude/commands/test_e2e.md`, then read and execute `.claude/commands/e2e/test_chart_visualization.md` to validate the new chart visualization functionality end-to-end.
- Read and execute `.claude/commands/e2e/test_basic_query.md` to confirm no regression in the basic query flow.
- Read and execute `.claude/commands/e2e/test_export_functionality.md` to confirm the Export and Hide buttons still work correctly alongside the new Visualize button.

## Notes
- New runtime dependency: `chart.js` (added via `bun add chart.js` in `app/client/`). Imported via `chart.js/auto` to register all controllers/elements automatically — this keeps the implementation simple at the cost of a slightly larger bundle. If bundle size becomes a concern, this can later be refactored to import only the specific controllers (`BarController`, `LineController`, `PieController`, `CategoryScale`, `LinearScale`, `Title`, `Tooltip`, `Legend`, `ArcElement`, `BarElement`, `LineElement`, `PointElement`).
- The feature is intentionally fully client-side: no backend changes, no API changes, no schema changes. This minimizes blast radius and keeps the change reviewable.
- Column type detection is heuristic (based on the actual values in the result set, not on the SQLite schema) because query results can include computed/aggregated columns whose declared type is unclear. This also handles the common case where SQLite stores numbers as strings.
- Excluding `id`/`rowid` from the *default* Y-axis selection (but still allowing them in the dropdown) avoids the common pitfall of charting row IDs by accident, while not blocking the user if those are genuinely the values they want.
- The panel is rendered inline below the SQL display rather than in a modal so users can see SQL, table, and chart together — useful for sanity-checking that the chart matches the data.
- No decorators are used; helper functions are kept simple and module-scoped to match the existing style of `main.ts`.
- Future considerations (out of scope): saving favorite chart configurations per query, exporting the chart as PNG, additional chart types (scatter, stacked bar, doughnut), grouping/aggregation controls (e.g., "sum Y per X" automatically when X has duplicates).
