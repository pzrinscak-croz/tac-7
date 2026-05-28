# Feature: Chart Visualization

## Metadata
issue_number: 4865d694
adw_id: {"number":40,"title":"1. Chart Visualization"}
issue_json: {"number":40,"title":"1. Chart Visualization","body":"/feature\n\nadw_sdlc_iso\n\nmodel_set heavy\n\nAfter a query returns results, show a \"Visualize\" button. Renders data as a bar, line, or pie chart using Chart.js. User picks chart type and which columns to use for axes. The chart must display actual data values -- not empty charts, flat lines, or zero-height bars.\n\n**Scope:**\n- Client-only change -- add Chart.js dependency, chart type selector, axis dropdowns\n- Renders from the same data already in the results table\n\n**Acceptance criteria:**\n1. Y-axis dropdown only offers numeric columns; X-axis dropdown only offers categorical/text columns -- never allow non-numeric data on the Y-axis (it renders as zeros)\n2. Auto-select sensible defaults: first text column for X, first numeric column (excluding `id`/`rowid`) for Y\n3. If no numeric columns exist, show \"No numeric columns available\" instead of an empty chart\n4. Bar chart bars have heights proportional to data values; Y-axis auto-scales to fit the data\n5. Pie chart slices are proportional to values with percentage labels; max 15 slices (remainder grouped as \"Other\")\n6. All Y-axis values are parsed as numbers before charting -- never pass raw strings to Chart.js\n7. Tooltips show exact values on hover; legend and axis labels are visible\n8. Chart has minimum 300px height and is readable without scrolling\n9. If results table has 0 rows, the Visualize button is hidden"}

## Feature Description
Add chart visualization capability to the Natural Language SQL Interface. After executing a query, users can click a "Visualize" button to render their results as an interactive chart (bar, line, or pie). The feature intelligently categorizes columns by data type, auto-selects sensible defaults, and ensures all chart values are properly parsed as numbers.

## User Story
As a data analyst
I want to visualize query results as interactive charts
So that I can quickly understand data patterns and share insights with stakeholders

## Problem Statement
Currently, users can only view query results in a table format. For datasets with numeric values, visual representations (bar charts, line charts, pie charts) provide faster insight into data distribution, trends, and proportions. The feature must correctly handle data types and ensure charts render actual values rather than empty or zero-value visualizations.

## Solution Statement
Implement a client-side chart visualization feature using Chart.js:
1. Add Chart.js as a dependency to the client
2. After query results are displayed, show a "Visualize" button (hidden when 0 rows)
3. Create a chart configuration modal/panel with:
   - Chart type selector (bar, line, pie)
   - X-axis column dropdown (categorical/text columns only)
   - Y-axis column dropdown (numeric columns only)
4. Auto-select first text column for X and first numeric column for Y (excluding id/rowid)
5. Parse all Y values as numbers before passing to Chart.js
6. Render the chart with proper sizing (min 300px height), tooltips, legends, and axis labels
7. For pie charts, limit to 15 slices with remainder grouped as "Other"

## Relevant Files

- `app/client/package.json` - Add Chart.js dependency
- `app/client/src/main.ts` - Add chart visualization logic and UI components
- `app/client/src/style.css` - Add styles for chart section, visualize button, and chart container
- `app/client/index.html` - No changes needed
- `app/client/src/types.d.ts` - No changes needed (uses existing QueryResponse type)

### New Files
- `.claude/commands/e2e/test_chart_visualization.md` - E2E test for chart visualization feature

## Implementation Plan

### Phase 1: Foundation
1. Add Chart.js dependency to package.json
2. Install the new dependency with `bun install`

### Phase 2: Core Implementation
1. Create helper functions to:
   - Classify columns as numeric vs categorical
   - Auto-select default X and Y columns
   - Parse values as numbers safely
   - Prepare chart data in Chart.js format
2. Add "Visualize" button to results header (only when results exist with rows)
3. Create chart configuration panel with:
   - Chart type selector (bar/line/pie)
   - X-axis dropdown (text columns only)
   - Y-axis dropdown (numeric columns only)
   - "Generate Chart" button
4. Implement chart rendering function with:
   - Proper axis labels
   - Visible legend
   - Tooltips showing exact values
   - Minimum 300px height
5. Add pie chart slice limiting (15 slices + "Other")

### Phase 3: Integration
1. Update displayResults to add Visualize button
2. Handle edge cases:
   - No numeric columns: show warning message
   - 0 result rows: hide Visualize button
   - Empty chart data: show appropriate message

## Step by Step Tasks

### Task 1: Add Chart.js Dependency
- Open `app/client/package.json`
- Add `"chart.js": "^4.4.0"` to dependencies
- Run `cd app/client && bun install`

### Task 2: Create E2E Test File
- Create `.claude/commands/e2e/test_chart_visualization.md` based on existing test patterns
- Test should validate:
  - Visualize button appears after query with results
  - Visualize button is hidden for 0-row results
  - Chart type selector works (bar/line/pie)
  - Column dropdowns filter correctly (numeric vs text)
  - Chart renders with actual data
  - Pie chart limits to 15 slices

### Task 3: Add Chart Configuration and Rendering Logic to main.ts
Add the following code sections to `app/client/src/main.ts`:

#### Helper Functions
```typescript
// Classify column as numeric or categorical
function isNumericColumn(values: any[]): boolean

// Get default X and Y column selections
function getDefaultChartColumns(results: Record<string, any>[], columns: string[]): { xColumn: string, yColumn: string }

// Parse value as number, returning null if not parseable
function parseNumericValue(value: any): number | null

// Prepare chart data for Chart.js
function prepareChartData(results: Record<string, any>[], xColumn: string, yColumn: string, chartType: string): ChartData
```

#### Chart Configuration UI
- Add `showVisualizeModal()` function to display chart configuration panel
- Chart type dropdown: bar, line, pie
- X-axis dropdown: filtered to show only text/categorical columns
- Y-axis dropdown: filtered to show only numeric columns
- Show warning if no numeric columns available

#### Chart Rendering
- Add `renderChart()` function using Chart.js
- Parse Y values as numbers before passing to Chart.js
- Set chart options for tooltips, legends, axis labels
- Minimum 300px height
- Pie chart: limit slices to 15, group remainder as "Other"

### Task 4: Add Visualize Button to Results Header
In `displayResults()` function:
- Only show Visualize button when `response.results.length > 0`
- Button positioned next to Export button

### Task 5: Add Chart Styles to style.css
Add CSS for:
- `.visualize-button` - styling for the visualize button
- `.chart-panel` - container for chart configuration
- `.chart-type-select` - chart type dropdown styling
- `.chart-axis-select` - axis dropdown styling
- `.chart-container` - chart canvas container with min 300px height
- `.chart-warning` - warning message styling for no numeric columns

### Task 6: Test and Validate
- Run TypeScript compilation: `cd app/client && bun tsc --noEmit`
- Build frontend: `cd app/client && bun run build`
- Run E2E test: execute `.claude/commands/e2e/test_chart_visualization.md`

## Testing Strategy

### Unit Tests
- Column classification: verify numeric vs categorical detection works correctly
- Value parsing: verify numbers are correctly parsed and invalid values handled
- Auto-selection: verify sensible defaults are chosen (first text for X, first numeric for Y excluding id/rowid)
- Pie chart slicing: verify 15-slice limit works with "Other" grouping

### Edge Cases
- Query with 0 results: Visualize button should be hidden
- Query with no numeric columns: should show "No numeric columns available" message
- Query with all numeric columns: X-axis dropdown should still show columns (can use numeric as labels)
- Empty string values: should be handled gracefully
- Very large datasets: should render efficiently

## Acceptance Criteria
1. Y-axis dropdown only offers numeric columns; X-axis dropdown only offers categorical/text columns
2. Auto-select sensible defaults: first text column for X, first numeric column (excluding `id`/`rowid`) for Y
3. If no numeric columns exist, show "No numeric columns available" instead of an empty chart
4. Bar chart bars have heights proportional to data values; Y-axis auto-scales to fit the data
5. Pie chart slices are proportional to values with percentage labels; max 15 slices (remainder grouped as "Other")
6. All Y-axis values are parsed as numbers before charting -- never pass raw strings to Chart.js
7. Tooltips show exact values on hover; legend and axis labels are visible
8. Chart has minimum 300px height and is readable without scrolling
9. If results table has 0 rows, the Visualize button is hidden

## Validation Commands
1. `cd app/client && bun tsc --noEmit` - Run frontend TypeScript check to validate the feature works with zero regressions
2. `cd app/client && bun run build` - Run frontend build to validate the feature works with zero regressions
3. Read `.claude/commands/test_e2e.md`, then read and execute `.claude/commands/e2e/test_chart_visualization.md` to validate chart visualization functionality works end-to-end

## Notes
- Chart.js v4.4.0 is the latest stable version with good TypeScript support
- The implementation uses vanilla TypeScript with Chart.js directly, no wrapper libraries needed
- Chart rendering happens entirely client-side using existing query results data
- Consider adding chart export functionality in a future iteration (PNG/SVG export)