# Feature: Chart Visualization

## Metadata
issue_number: `ec0b97a0`
adw_id: `4`
issue_json: ``

## Feature Description
Add chart visualization capability to the Natural Language SQL Interface. After a query returns results, a "Visualize" button appears that opens a chart panel. Users can select from bar, line, or pie chart types and choose which columns to use for X and Y axes. The chart renders actual data values using Chart.js. This is a client-only change — no backend modifications needed.

## User Story
As a data analyst
I want to visualize my query results as bar, line, or pie charts
So that I can quickly understand data patterns and distributions without exporting to external tools

## Problem Statement
Currently, query results are displayed only as a table. Users who want to visualize trends, distributions, or comparisons must export data and use external charting tools. This adds friction to the data exploration workflow.

## Solution Statement
Add Chart.js as a client dependency and build a visualization panel that renders query result data as charts. The panel includes a chart type selector (bar/line/pie), axis column dropdowns (X: categorical/text, Y: numeric only), and auto-selects sensible defaults. The chart integrates alongside the existing results table, using the same data already available in the `QueryResponse`.

## Relevant Files
Use these files to implement the feature:

- `app/client/package.json` — Add Chart.js dependency here
- `app/client/src/main.ts` — Main application logic; add Visualize button in `displayResults()`, chart rendering functions, axis selection logic. This is the primary implementation file.
- `app/client/src/style.css` — Add chart container, chart controls, and visualization panel styles. Read this file first to understand existing CSS patterns and variables.
- `app/client/src/types.d.ts` — Add any chart-related type definitions if needed
- `app/client/index.html` — Add chart container markup to the results section
- `.claude/commands/test_e2e.md` — Read to understand E2E test runner framework
- `.claude/commands/e2e/test_basic_query.md` — Read as E2E test example for format reference

### New Files
- `.claude/commands/e2e/test_chart_visualization.md` — E2E test for chart visualization feature

## Implementation Plan
### Phase 1: Foundation
Install Chart.js dependency and add the HTML markup for the chart panel (canvas element, chart type selector, axis dropdowns) within the results section of `index.html`. Define any necessary TypeScript types.

### Phase 2: Core Implementation
Implement the chart rendering logic in `main.ts`:
- Column classification (numeric vs. categorical) by inspecting query result data
- Auto-selection of sensible defaults (first text column for X, first numeric column excluding id/rowid for Y)
- Chart creation/destruction lifecycle using Chart.js
- Axis dropdown population and change handlers
- Pie chart slice grouping (max 15 slices, remainder as "Other")
- Number parsing for all Y-axis values before passing to Chart.js

### Phase 3: Integration
Wire the Visualize button into the existing `displayResults()` flow. Add CSS styling consistent with the existing card-based UI. Ensure the chart panel toggles visibility alongside the results table. Handle edge cases (0 rows, no numeric columns).

## Step by Step Tasks

### Task 1: Install Chart.js Dependency
- Run `cd app/client && bun add chart.js` to add Chart.js as a project dependency
- Verify `package.json` is updated with the chart.js entry

### Task 2: Add Chart HTML Markup
- Edit `app/client/index.html` to add a chart visualization panel inside the results section (after the results container)
- Add a `<div id="chart-panel">` containing:
  - A controls row with: chart type selector (`<select>` with bar/line/pie options), X-axis column dropdown, Y-axis column dropdown
  - A `<canvas id="chart-canvas">` element for Chart.js rendering
  - A "No numeric columns available" message element (hidden by default)
- The chart panel should be hidden by default (`style="display: none;"`)

### Task 3: Add Chart Styles
- Read `app/client/src/style.css` to understand existing CSS patterns and variables
- Add styles for:
  - `.chart-panel` — card-like container matching existing surface styling, min-height 300px
  - `.chart-controls` — flexbox row for chart type selector and axis dropdowns
  - `.chart-controls select` — styled to match existing button/input patterns
  - `#chart-canvas` — responsive canvas with min-height 300px
  - `.no-numeric-message` — styled message for when no numeric columns exist
  - `.visualize-button` — styled consistently with existing `.secondary-button`

### Task 4: Implement Chart Logic in main.ts
- Import Chart.js: `import { Chart, registerables } from 'chart.js'; Chart.register(...registerables);`
- Implement helper function `classifyColumns(results, columns)`:
  - Iterate through result rows to determine which columns contain numeric data
  - A column is numeric if the majority of non-null values can be parsed as numbers
  - Exclude columns named `id`, `rowid`, or ending with `_id` from Y-axis candidates
  - Return `{ numericColumns: string[], categoricalColumns: string[] }`
- Implement helper function `getDefaultAxes(numericColumns, categoricalColumns)`:
  - X-axis default: first categorical/text column
  - Y-axis default: first numeric column (excluding id/rowid patterns)
  - Return `{ xColumn: string | null, yColumn: string | null }`
- Implement `renderChart(results, columns, chartType, xColumn, yColumn)`:
  - Destroy existing chart instance if any (via `chart.destroy()`)
  - Parse all Y-axis values as numbers using `parseFloat()`, filtering out NaN
  - For pie charts: limit to 15 slices, group remainder as "Other" with summed value; add percentage labels
  - For bar/line charts: auto-scale Y-axis to fit data
  - Configure tooltips to show exact values on hover
  - Configure visible legend and axis labels
  - Set chart options for responsive sizing with min-height 300px
- Implement `initializeChartPanel(response)`:
  - Classify columns from `response.results` and `response.columns`
  - If no numeric columns exist, show "No numeric columns available" message and hide chart canvas
  - Populate X-axis dropdown with categorical columns, Y-axis dropdown with numeric columns
  - Set default selections
  - Attach change event listeners to dropdowns and chart type selector to re-render chart
  - Render initial chart with defaults

### Task 5: Integrate Visualize Button into displayResults()
- In `displayResults()` function, after the export button creation block:
  - If `response.results.length > 0`: create a "Visualize" button with class `visualize-button secondary-button`
  - Add chart icon SVG inline (simple bar chart icon)
  - On click: toggle chart panel visibility and call `initializeChartPanel(response)` on first show
  - Add the Visualize button to the `buttonContainer` (alongside Export and Hide buttons)
- If `response.results.length === 0`: ensure chart panel is hidden and Visualize button is not created
- When results are re-displayed (new query), destroy any existing chart and hide the chart panel

### Task 6: Create E2E Test File
- Read `.claude/commands/test_e2e.md` and `.claude/commands/e2e/test_basic_query.md` for format reference
- Create `.claude/commands/e2e/test_chart_visualization.md` with test steps:
  1. Navigate to application URL
  2. Take screenshot of initial state
  3. Load sample data (click Upload Data, use a sample dataset with numeric columns)
  4. Enter a query that returns results with numeric data (e.g., "Show me all data from the users table")
  5. Click Query button
  6. **Verify** results appear with data rows
  7. **Verify** a "Visualize" button is visible in the results header
  8. Take screenshot showing results with Visualize button
  9. Click the Visualize button
  10. **Verify** chart panel appears with chart type selector, X-axis dropdown, Y-axis dropdown
  11. **Verify** Y-axis dropdown only contains numeric columns
  12. **Verify** a bar chart is rendered by default with visible bars (non-zero height)
  13. Take screenshot of the bar chart
  14. Change chart type to "Line"
  15. **Verify** a line chart is rendered
  16. Take screenshot of the line chart
  17. Change chart type to "Pie"
  18. **Verify** a pie chart is rendered with percentage labels
  19. Take screenshot of the pie chart
  20. Click Visualize button again to hide the chart panel
  21. **Verify** chart panel is hidden
  22. Take screenshot of final state

### Task 7: Run Validation Commands
- Execute all validation commands listed below to ensure zero regressions

## Testing Strategy
### Unit Tests
- No server-side unit tests needed (client-only change)
- TypeScript compilation (`tsc --noEmit`) validates type safety
- Production build (`bun run build`) validates bundling with Chart.js

### Edge Cases
- Query returns 0 rows → Visualize button should not appear
- Query returns data with no numeric columns → show "No numeric columns available" message
- Query returns data with only numeric columns → X-axis uses first column, Y-axis uses second
- Pie chart with more than 15 unique X values → group into 15 slices + "Other"
- Y-axis values containing null or non-numeric strings → parse as numbers, skip NaN values
- Switching chart types rapidly → previous chart instance destroyed before creating new one
- Re-running a query while chart is visible → chart panel resets

## Acceptance Criteria
- Visualize button appears in results header when query returns rows with data
- Visualize button is hidden when results have 0 rows
- Y-axis dropdown only offers numeric columns; X-axis only offers categorical/text columns
- Auto-selects first text column for X, first numeric column (excluding id/rowid) for Y
- "No numeric columns available" message shown when no numeric columns exist
- Bar chart bars have heights proportional to data values; Y-axis auto-scales
- Line chart renders data points connected by lines
- Pie chart slices proportional to values with percentage labels; max 15 slices (remainder grouped as "Other")
- All Y-axis values parsed as numbers before charting
- Tooltips show exact values on hover; legend and axis labels visible
- Chart has minimum 300px height and is readable without scrolling
- TypeScript compiles without errors
- Production build succeeds
- E2E test passes

## Validation Commands
Execute every command to validate the feature works correctly with zero regressions.

- `cd app/client && bun install` - Install dependencies including new Chart.js package
- `cd app/client && bun tsc --noEmit` - Run TypeScript type checking to validate no type errors
- `cd app/client && bun run build` - Run production build to validate Chart.js bundles correctly
- `cd app/server && uv run pytest` - Run server tests to validate zero regressions
- Read `.claude/commands/test_e2e.md`, then read and execute `.claude/commands/e2e/test_chart_visualization.md` E2E test to validate chart visualization works end-to-end

## Notes
- **New dependency**: Chart.js will be added via `bun add chart.js`. Chart.js is a well-maintained, lightweight charting library with TypeScript support built-in.
- The implementation is entirely client-side — no backend API changes required.
- Chart.js handles responsive canvas sizing natively; we set `responsive: true` and `maintainAspectRatio: false` in chart options.
- The chart instance must be explicitly destroyed before creating a new one to prevent memory leaks (Chart.js requirement).
- Color palette for chart datasets should use the existing CSS variable `--primary-color` (#667eea) and complementary colors for multi-series data.
