# Chart Visualization

**ADW ID:** 16
**Date:** 2026-03-26
**Specification:** specs/issue-3b457493-adw-16-sdlc_planner-add-chart-visualization.md

## Overview

Added an interactive chart visualization capability to the Natural Language SQL Interface. After running a query, users can click a "Visualize" button to render results as bar, line, or pie charts using Chart.js, with selectable axes and automatic column type detection. This is a client-only feature that works with the existing query results data.

## What Was Built

- Chart.js integration as a frontend dependency
- Column type detection utilities that analyze actual data values to classify columns as numeric or categorical
- Interactive chart controls (chart type selector, X-axis dropdown, Y-axis dropdown)
- Chart rendering engine supporting bar, line, and pie chart types
- Pie chart grouping that consolidates slices beyond 15 into an "Other" category
- Automatic default axis selection (first categorical column for X, first non-id numeric column for Y)
- Chart cleanup on re-query and toggle show/hide behavior

## Technical Implementation

### Files Modified

- `app/client/package.json`: Added `chart.js` ^4.5.1 as a production dependency
- `app/client/src/main.ts`: Added Chart.js imports, column detection utilities (`getNumericColumns`, `getCategoricalColumns`), chart rendering logic (`renderChart`, `destroyChart`), and Visualize button with controls UI in `displayResults()`
- `app/client/src/style.css`: Added styles for `.chart-section`, `.chart-controls`, `.chart-control-group`, `.chart-canvas-container`, `.visualize-button`, and `.no-numeric-message`

### Key Changes

- **Column detection**: `getNumericColumns()` filters columns by checking if all non-empty values parse as numbers via `Number()` / `isNaN()`. `getCategoricalColumns()` returns the complement, falling back to all columns if none are purely categorical.
- **Chart rendering**: `renderChart()` creates Chart.js instances with responsive layout, tooltips showing exact values, legends, axis labels, and auto-scaling. Pie charts show percentage in tooltips.
- **Pie chart grouping**: When data exceeds 15 points, the top 14 values are kept individually and the rest are summed into an "Other" slice.
- **All-numeric edge case**: When no categorical columns exist, a synthetic "Row Index" column is used for the X-axis.
- **Lifecycle management**: Previous chart instances are destroyed before re-rendering, and chart sections are cleaned up when new queries are executed.

## How to Use

1. Enter a natural language query and submit it
2. When results appear with numeric columns, a **Visualize** button appears in the results header alongside Export and Hide buttons
3. Click **Visualize** to open the chart panel below the results table
4. Use the **Chart Type** dropdown to switch between Bar, Line, and Pie views
5. Use the **X-Axis** dropdown to select which column provides labels (categorical columns)
6. Use the **Y-Axis** dropdown to select which column provides values (numeric columns only)
7. Charts update automatically when any selector is changed
8. Click **Hide Chart** to collapse the chart panel

## Configuration

No additional configuration is required. Chart.js is bundled with the client build automatically.

## Testing

- TypeScript compilation: `cd app/client && bun tsc --noEmit`
- Production build: `cd app/client && bun run build`
- Server regression tests: `cd app/server && uv run pytest`
- E2E test: Run the chart visualization E2E test defined in `.claude/commands/e2e/test_chart_visualization.md`

## Notes

- The Visualize button only appears when query results contain at least one numeric column and at least one row
- Columns named `id` or `rowid` are skipped when auto-selecting the default Y-axis, but remain available in the dropdown
- Null and empty values in numeric columns are treated as 0 by `Number()` parsing
- Chart.js handles rendering performance for large datasets; pie chart grouping mitigates visual clutter beyond 15 slices
