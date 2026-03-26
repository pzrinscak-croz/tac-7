# Feature: Chart Visualization

## Metadata
issue_number: `3b457493`
adw_id: `16`
issue_json: ``

## Feature Description
Add a chart visualization capability to the Natural Language SQL Interface. After a query returns results, users can click a "Visualize" button to render the data as a bar, line, or pie chart using Chart.js. Users select the chart type and which columns to use for X/Y axes via dropdown selectors. The chart displays actual data values with proper scaling, tooltips, and labels. This is a client-only change that renders from the same data already available in the results table.

## User Story
As a non-technical user querying data with natural language
I want to visualize query results as bar, line, or pie charts
So that I can quickly understand trends and distributions without exporting data to a separate tool

## Problem Statement
Currently, query results are only displayed as an HTML table. Users who want to visualize patterns, distributions, or trends must export to CSV and open in a separate tool. This breaks the workflow and limits the value of the natural language query interface for quick data exploration.

## Solution Statement
Add Chart.js as a frontend dependency and create chart rendering functions in `main.ts` that:
1. Show a "Visualize" button in the results header when numeric columns exist
2. Provide a chart type selector (bar, line, pie) and axis column dropdowns
3. Automatically detect numeric vs text columns and set sensible defaults
4. Render charts with proper scaling, tooltips, legends, and minimum 300px height
5. Group pie chart slices beyond 15 into "Other"
6. Parse all Y-axis values as numbers before passing to Chart.js

## Relevant Files
Use these files to implement the feature:

- `app/client/package.json` — Add Chart.js dependency here
- `app/client/src/main.ts` — All frontend logic lives here; add chart initialization, rendering functions, column detection, and UI controls
- `app/client/src/style.css` — Add chart container, controls, and dropdown styles matching existing design patterns (CSS variables, card layout)
- `app/client/index.html` — No changes needed; chart UI will be dynamically created in the results section via DOM manipulation (matching existing patterns)
- `app/client/src/types.d.ts` — No changes needed; uses existing `QueryResponse` type with `results` and `columns`
- `app/client/tsconfig.json` — May need to verify Chart.js types are resolved
- Read `.claude/commands/test_e2e.md` and `.claude/commands/e2e/test_basic_query.md` to understand how to create an E2E test file

### New Files
- `.claude/commands/e2e/test_chart_visualization.md` — E2E test validating chart visualization feature

## Implementation Plan
### Phase 1: Foundation
- Install Chart.js as a dependency via `bun add chart.js`
- Implement column type detection utility functions: `getNumericColumns()` and `getCategoricalColumns()` that analyze the actual data values in `results` to determine which columns contain numeric data
- These functions must check actual cell values (not just column names) since SQLite types may not perfectly indicate numeric vs text

### Phase 2: Core Implementation
- Add chart container and controls UI (chart type selector dropdown, X-axis dropdown, Y-axis dropdown) created dynamically in the `displayResults()` function
- Implement `renderChart()` function that:
  - Parses all Y-axis values as `Number()` before passing to Chart.js
  - Creates bar/line charts with auto-scaled Y-axis and proper axis labels
  - Creates pie charts with percentage labels, max 15 slices (remainder grouped as "Other")
  - Sets minimum 300px canvas height
  - Shows tooltips with exact values on hover
  - Shows legend and axis labels
- Implement `destroyChart()` to clean up previous Chart.js instances before re-rendering
- Handle defaults: auto-select first text column for X, first numeric column (excluding `id`/`rowid`) for Y

### Phase 3: Integration
- Add "Visualize" button to results header (next to Export and Hide buttons) — only shown when results have rows AND numeric columns exist
- Wire up controls: changing chart type or axis columns triggers re-render
- Show "No numeric columns available" message when no numeric columns exist in results
- Hide Visualize button when results have 0 rows
- Add CSS for chart controls, container, and no-data message matching existing design system

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

### Task 1: Install Chart.js dependency
- Run `cd app/client && bun add chart.js`
- Verify `chart.js` appears in `package.json` dependencies

### Task 2: Create E2E test file for chart visualization
- Read `.claude/commands/test_e2e.md` and `.claude/commands/e2e/test_basic_query.md` for format reference
- Create `.claude/commands/e2e/test_chart_visualization.md` with test steps:
  1. Navigate to the application
  2. Load sample data (users or products)
  3. Run a query that returns numeric results (e.g., "Show me all products with their prices")
  4. Verify Visualize button appears in results header
  5. Click Visualize button
  6. Verify chart controls appear (chart type selector, X-axis dropdown, Y-axis dropdown)
  7. Verify Y-axis dropdown only contains numeric columns
  8. Verify X-axis dropdown only contains text/categorical columns
  9. Verify a chart canvas is rendered with visible bars/data
  10. Take screenshot of chart with bar type
  11. Change chart type to "pie" and verify chart re-renders
  12. Take screenshot of pie chart
  13. Change chart type to "line" and verify chart re-renders
  14. Take screenshot of line chart
- Success criteria: charts render with actual data, controls work, proper column filtering

### Task 3: Add column type detection utilities in main.ts
- Add `getNumericColumns(results, columns)` function that:
  - Iterates through each column and checks if values can be parsed as numbers
  - Excludes columns where all values are null/empty
  - Returns array of column names that contain numeric data
- Add `getCategoricalColumns(results, columns)` function that:
  - Returns columns that are NOT numeric (text/categorical)
  - Falls back to all columns if no purely categorical columns found
- Both functions analyze actual cell values using `Number()` / `isNaN()`, not column type metadata

### Task 4: Add chart CSS styles to style.css
- Add `.chart-section` container style (margin-top, padding, matching card design with border-radius: 8px)
- Add `.chart-controls` flexbox layout for dropdowns and chart type selector (gap: 1rem, flex-wrap: wrap)
- Add `.chart-control-group` for label + dropdown pairs
- Add `.chart-control-group label` styling (font-weight 600, color: var(--text-secondary))
- Add `.chart-control-group select` styling matching existing button/input styles (padding, border, border-radius: 6px)
- Add `.chart-canvas-container` with min-height: 300px
- Add `.no-numeric-message` info style (similar to existing info/error message patterns)
- Add `.visualize-button` style extending `.secondary-button` pattern

### Task 5: Implement chart rendering logic in main.ts
- Import Chart.js at the top: `import { Chart, registerables } from 'chart.js'` and call `Chart.register(...registerables)`
- Add module-level variable: `let currentChart: Chart | null = null`
- Implement `destroyChart()` that calls `currentChart.destroy()` and sets to null
- Implement `renderChart(results, xColumn, yColumn, chartType, canvasElement)`:
  - Extract labels from `results.map(r => String(r[xColumn]))`
  - Extract data from `results.map(r => Number(r[yColumn]))` — parse as numbers
  - For pie charts with >15 data points: take top 14 by value, sum the rest as "Other"
  - For pie chart: add `datalabels` or use tooltip plugin to show percentage labels
  - Configure chart with:
    - `responsive: true, maintainAspectRatio: false`
    - Tooltips showing exact values
    - Legend visible
    - Y-axis auto-scaling (for bar/line)
    - Axis labels showing column names
    - Color palette using CSS variable colors + generated palette

### Task 6: Implement Visualize button and chart controls UI in displayResults()
- In `displayResults()`, after the export button logic:
  - Detect numeric columns using `getNumericColumns(response.results, response.columns)`
  - If results have rows AND numeric columns exist: create and show Visualize button in results header buttons container
  - If no numeric columns: do NOT show Visualize button
  - If 0 rows: do NOT show Visualize button (already handled by existing `response.results.length > 0` check)
- On Visualize button click:
  - Create/show chart section below results container with:
    - Chart type `<select>` (Bar, Line, Pie)
    - X-axis `<select>` populated with categorical columns
    - Y-axis `<select>` populated with numeric columns
  - Auto-select defaults: first categorical column for X, first numeric column (skip `id`/`rowid`) for Y
  - Render chart with defaults
  - Toggle button text between "Visualize" and "Hide Chart"
- Wire change events on all three dropdowns to call `renderChart()` with updated selections
- If no numeric columns exist but Visualize is somehow triggered, show "No numeric columns available" message

### Task 7: Handle edge cases
- When query returns 0 rows: Visualize button is already hidden (inside `response.results.length > 0` block)
- When no numeric columns: Visualize button not rendered; if chart section exists from previous query, remove it
- When all columns are numeric (no categorical): use row index as X-axis labels
- Destroy previous chart instance before creating a new one on re-render or new query
- Clean up chart section when a new query is executed (in `displayResults()` at the start)

### Task 8: Run validation commands
- Run `cd app/server && uv run pytest` to ensure no server regressions
- Run `cd app/client && bun tsc --noEmit` to validate TypeScript compiles
- Run `cd app/client && bun run build` to validate production build
- Read `.claude/commands/test_e2e.md`, then read and execute `.claude/commands/e2e/test_chart_visualization.md` E2E test

## Testing Strategy
### Unit Tests
- No separate unit test files needed (vanilla TS app has no unit test framework configured)
- Validation via TypeScript compilation (`bun tsc --noEmit`) and production build (`bun run build`)
- E2E test covers functional validation

### Edge Cases
- Query returns 0 rows → Visualize button hidden
- Query returns only text columns (no numeric) → Visualize button not shown, "No numeric columns available" if somehow accessed
- Query returns only numeric columns → Use row index for X-axis
- Column named `id` or `rowid` → Skipped as default Y-axis selection (but still available in dropdown)
- Very large dataset → Chart.js handles rendering; pie chart groups beyond 15 slices
- Null/empty values in numeric column → `Number(null)` = 0, `Number('')` = 0; filter or treat as 0
- Mixed numeric/text values in a column → Column classified based on majority; `Number()` parsing handles edge cases
- Re-running a query → Previous chart destroyed, new chart section created

## Acceptance Criteria
1. Y-axis dropdown only offers numeric columns; X-axis dropdown only offers categorical/text columns
2. Auto-selects first text column for X, first numeric column (excluding `id`/`rowid`) for Y
3. If no numeric columns exist, Visualize button is not shown
4. Bar chart bars have heights proportional to data values; Y-axis auto-scales
5. Pie chart slices are proportional with percentage labels; max 15 slices (remainder grouped as "Other")
6. All Y-axis values are parsed as numbers before charting
7. Tooltips show exact values on hover; legend and axis labels visible
8. Chart has minimum 300px height and is readable without scrolling
9. If results table has 0 rows, the Visualize button is hidden
10. TypeScript compiles without errors
11. Production build succeeds
12. E2E test passes

## Validation Commands
Execute every command to validate the feature works correctly with zero regressions.

- `cd app/server && uv run pytest` - Run server tests to validate the feature works with zero regressions
- `cd app/client && bun tsc --noEmit` - Run frontend tests to validate the feature works with zero regressions
- `cd app/client && bun run build` - Run frontend build to validate the feature works with zero regressions
- Read `.claude/commands/test_e2e.md`, then read and execute `.claude/commands/e2e/test_chart_visualization.md` E2E test to validate this functionality works

## Notes
- Chart.js is specified in the issue requirements — use `chart.js` (not D3, Recharts, etc.)
- This is a client-only change — no backend modifications needed
- The `chart.js` package includes TypeScript types (`chart.js/auto` or `chart.js` with registerables)
- For pie chart percentage labels, use Chart.js built-in tooltip callbacks rather than adding the `chartjs-plugin-datalabels` dependency to keep the dependency footprint minimal
- The existing app uses vanilla TypeScript DOM manipulation — follow the same pattern for chart UI (no framework components)
- New library: `chart.js` added via `cd app/client && bun add chart.js`
