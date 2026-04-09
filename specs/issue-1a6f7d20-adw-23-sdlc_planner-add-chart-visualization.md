# Feature: Chart Visualization

## Metadata
issue_number: `1a6f7d20`
adw_id: `23`
issue_json: ``

## Feature Description
Add a chart visualization capability to the Natural Language SQL Interface. After a query returns results, a "Visualize" button appears that lets users render data as bar, line, or pie charts using Chart.js. Users can pick the chart type and select which columns to use for X and Y axes. The chart displays actual data values with proper scaling, tooltips, and legends. This is a client-only change that renders from the same data already in the results table.

## User Story
As a data analyst using the Natural Language SQL Interface
I want to visualize my query results as bar, line, or pie charts
So that I can quickly understand patterns and distributions in my data without exporting to another tool

## Problem Statement
Currently, query results are only displayed as a raw table. Users cannot visually analyze trends, distributions, or comparisons without exporting data to a separate charting tool. This creates friction and slows down data exploration workflows.

## Solution Statement
Add Chart.js as a client dependency and create a chart visualization module that integrates with the existing `displayResults()` flow. When query results contain numeric data, a "Visualize" button appears in the results header. Clicking it reveals chart controls (chart type selector, X-axis dropdown for categorical columns, Y-axis dropdown for numeric columns) and renders a Chart.js canvas. The implementation enforces type safety by only allowing numeric columns on Y-axis and auto-selects sensible defaults.

## Relevant Files
Use these files to implement the feature:

- `app/client/package.json` — Add `chart.js` dependency
- `app/client/src/main.ts` — Modify `displayResults()` to add Visualize button and integrate chart rendering; this is the main integration point
- `app/client/src/types.d.ts` — No changes needed (QueryResponse already has `results` and `columns`)
- `app/client/src/style.css` — Add styles for chart container, controls (dropdowns, chart type selector), and Visualize button
- `app/client/index.html` — No changes needed (chart DOM elements created dynamically)
- `app/client/vite.config.ts` — No changes needed (Vite handles Chart.js import automatically)
- `app/client/tsconfig.json` — May need to verify module resolution settings for Chart.js imports
- `.claude/commands/test_e2e.md` — Read to understand E2E test runner pattern
- `.claude/commands/e2e/test_basic_query.md` — Read as template for creating new E2E test

### New Files
- `app/client/src/chart.ts` — Chart visualization module: column classification (numeric vs text), chart rendering, controls creation, Chart.js lifecycle management
- `.claude/commands/e2e/test_chart_visualization.md` — E2E test file for validating chart visualization functionality

## Implementation Plan
### Phase 1: Foundation
Install Chart.js dependency and create the chart module with helper functions for column type detection (numeric vs categorical), data parsing, and Chart.js configuration generation. Establish the module's public API that `main.ts` will call.

### Phase 2: Core Implementation
Build the chart rendering engine in `chart.ts`: chart type selector (bar/line/pie), axis column dropdowns with proper filtering (numeric-only Y, text-only X), canvas management, and Chart.js instance lifecycle (create/destroy). Implement all acceptance criteria: auto-defaults, pie slice grouping, number parsing, empty-state handling.

### Phase 3: Integration
Wire the chart module into `main.ts` `displayResults()` function. Add the Visualize button to the results header alongside existing Export and Hide buttons. Add CSS styles for chart controls and container. Create E2E test to validate the feature end-to-end.

## Step by Step Tasks

### Task 1: Install Chart.js dependency
- Run `cd app/client && bun install chart.js` to add Chart.js as a dependency
- Verify `package.json` is updated with `chart.js`

### Task 2: Create E2E test file
- Read `.claude/commands/test_e2e.md` and `.claude/commands/e2e/test_basic_query.md` to understand the E2E test pattern
- Create `.claude/commands/e2e/test_chart_visualization.md` with steps to:
  1. Navigate to the application URL
  2. Load sample "Product Inventory" data (has numeric price/quantity columns)
  3. Run a query like "Show me all products with their prices"
  4. Take screenshot of results table
  5. Verify the "Visualize" button is visible
  6. Click the "Visualize" button
  7. Verify chart controls appear (chart type selector, X-axis dropdown, Y-axis dropdown)
  8. Verify Y-axis dropdown only contains numeric columns
  9. Verify X-axis dropdown only contains text/categorical columns
  10. Verify a bar chart is rendered with visible bars (non-zero height)
  11. Take screenshot of the chart
  12. Switch chart type to "Pie" and verify pie chart renders
  13. Take screenshot of pie chart
  14. Switch chart type to "Line" and verify line chart renders
  15. Take screenshot of line chart

### Task 3: Create chart visualization module (`app/client/src/chart.ts`)
- Create the chart module with these exports:
  - `classifyColumns(results, columns)` — Returns `{ numeric: string[], text: string[] }` by inspecting actual data values. A column is numeric if every non-null value parses as a finite number. Exclude columns named `id` or `rowid` (case-insensitive) from numeric list.
  - `createChartControls(numericColumns, textColumns, onUpdate)` — Returns an HTMLDivElement containing:
    - Chart type selector with options: Bar, Line, Pie
    - X-axis dropdown populated with text columns
    - Y-axis dropdown populated with numeric columns
    - Auto-selects first text column for X, first numeric column for Y
  - `renderChart(canvas, chartType, labels, values, xLabel, yLabel)` — Creates/replaces a Chart.js instance on the given canvas element. Handles:
    - Bar: heights proportional to values, auto-scaled Y-axis
    - Line: data points connected, auto-scaled Y-axis
    - Pie: slices proportional to values, percentage labels, max 15 slices (group remainder as "Other")
    - Tooltips with exact values on hover
    - Visible legend and axis labels
  - `destroyChart()` — Destroys current Chart.js instance to prevent memory leaks
- Parse all Y-axis values as `Number()` before passing to Chart.js — never pass raw strings
- If no numeric columns exist, `createChartControls` returns a div with "No numeric columns available for charting" message

### Task 4: Add chart styles to `app/client/src/style.css`
- Add styles for:
  - `.chart-section` — Container for chart controls and canvas, minimum 300px height
  - `.chart-controls` — Flexbox row for chart type selector and axis dropdowns, with appropriate spacing
  - `.chart-type-selector` — Styled select/button group for Bar/Line/Pie
  - `.chart-axis-select` — Styled dropdown for axis column selection with labels
  - `.chart-canvas-container` — Wrapper for the canvas element, responsive width, min-height 300px
  - `.visualize-button` — Styled like existing `.secondary-button` but with a chart icon/indicator
  - `.no-numeric-message` — Style for the "No numeric columns available" message
- Use existing CSS variables (`--primary-color`, `--surface`, `--border-color`, etc.) for consistency

### Task 5: Integrate chart module into `main.ts`
- Import chart module functions at the top of `main.ts`
- Modify `displayResults()` function:
  - After the existing export button logic (around line 226-261), add a Visualize button to the `buttonContainer` div
  - Only show Visualize button when `response.results.length > 0` (AC #9)
  - On Visualize button click:
    1. Call `classifyColumns(response.results, response.columns)` to get numeric/text columns
    2. If no numeric columns, show "No numeric columns available" message (AC #3)
    3. Create chart controls with `createChartControls()` and append below the results table
    4. Create a canvas element inside a `.chart-canvas-container` div
    5. Call `renderChart()` with the default selections
    6. Wire up control change events to re-render the chart with new selections
  - Toggle behavior: clicking Visualize again hides the chart section
  - Call `destroyChart()` when new query results arrive (before rendering new results)

### Task 6: Run validation commands
- Run `cd app/server && uv run pytest` to verify no server regressions
- Run `cd app/client && bun tsc --noEmit` to verify TypeScript compiles without errors
- Run `cd app/client && bun run build` to verify production build succeeds
- Read `.claude/commands/test_e2e.md`, then read and execute `.claude/commands/e2e/test_chart_visualization.md` E2E test to validate the feature works end-to-end

## Testing Strategy
### Unit Tests
- No separate unit test files needed (vanilla TS app with no test framework on client)
- TypeScript compiler (`tsc --noEmit`) validates type safety of all chart module code
- E2E tests via Playwright validate the full user flow

### Edge Cases
- Query returns 0 rows: Visualize button should be hidden
- Query returns only text columns (no numeric): show "No numeric columns available" message
- Query returns only numeric columns (no text): X-axis should still work using row index or the available columns
- Column values contain nulls: skip null values when parsing numbers
- Column values contain mixed types (e.g., "N/A" in a mostly-numeric column): column classified as text
- Pie chart with more than 15 categories: group extras as "Other" slice
- Very large values: Y-axis auto-scales correctly
- Very small values: bars/lines are still visible
- Single row of data: chart renders without errors
- Column named `id` or `rowid`: excluded from numeric Y-axis dropdown defaults

## Acceptance Criteria
1. Y-axis dropdown only offers numeric columns; X-axis dropdown only offers categorical/text columns
2. Auto-select sensible defaults: first text column for X, first numeric column (excluding `id`/`rowid`) for Y
3. If no numeric columns exist, show "No numeric columns available" instead of an empty chart
4. Bar chart bars have heights proportional to data values; Y-axis auto-scales to fit the data
5. Pie chart slices are proportional to values with percentage labels; max 15 slices (remainder grouped as "Other")
6. All Y-axis values are parsed as numbers before charting — never pass raw strings to Chart.js
7. Tooltips show exact values on hover; legend and axis labels are visible
8. Chart has minimum 300px height and is readable without scrolling
9. If results table has 0 rows, the Visualize button is hidden

## Validation Commands
Execute every command to validate the feature works correctly with zero regressions.

- `cd app/client && bun tsc --noEmit` — Run frontend type checking to validate TypeScript compiles with zero errors
- `cd app/client && bun run build` — Run frontend production build to validate the feature builds correctly
- `cd app/server && uv run pytest` — Run server tests to validate no regressions
- Read `.claude/commands/test_e2e.md`, then read and execute `.claude/commands/e2e/test_chart_visualization.md` E2E test to validate chart visualization works end-to-end

## Notes
- **New dependency**: `chart.js` must be added via `cd app/client && bun install chart.js`
- **Client-only change**: No backend modifications needed. Charts render from the same `results[]` and `columns[]` data already returned by the query API.
- **Chart.js version**: Use latest stable (v4.x). It ships with TypeScript types built-in, so no separate `@types/chart.js` package is needed.
- **Module structure**: Creating a separate `chart.ts` module keeps chart logic isolated from `main.ts` and follows the existing pattern of `api/client.ts` being a separate module.
- **Canvas lifecycle**: Chart.js requires explicit `.destroy()` before re-rendering on the same canvas. The `destroyChart()` function handles this to prevent memory leaks and rendering artifacts.
- **Pie chart "Other" grouping**: When data has >15 categories, sum the smallest values into an "Other" slice. Sort by value descending, keep top 14, group the rest.
