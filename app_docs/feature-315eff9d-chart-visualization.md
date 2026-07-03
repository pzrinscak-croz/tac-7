# Chart Visualization

**ADW ID:** 315eff9d
**Date:** 2026-07-03
**Specification:** specs/issue-48-adw-315eff9d-sdlc_planner-chart-visualization.md

## Overview

Adds a client-side **Visualize** button to the query results header that renders the current results as a bar, line, or pie chart using [Chart.js](https://www.chartjs.org/). Users pick the chart type and which columns map to the X and Y axes, with the Y-axis restricted to numeric columns so charts always display real, proportional data values rather than empty charts, flat lines, or zero-height bars. This is a purely client-only change — the chart renders from the same data already shown in the results table.

## What Was Built

- A **Visualize** button in the results header, shown only when a query returns at least one row.
- An inline chart panel with a chart-type selector (Bar / Line / Pie), an X-axis dropdown, a Y-axis dropdown, and a Chart.js `<canvas>`.
- Automatic column classification that offers only numeric columns for the Y-axis and only categorical/text columns for the X-axis.
- Sensible default axis selection (first text column for X; first numeric column excluding `id`/`rowid` for Y).
- Numeric coercion of all Y values before charting, so string-stored numbers still render proportionally.
- Edge-case handling: "No numeric columns available" message, hidden Visualize button on zero-row results, and pie-slice grouping into "Other" beyond 15 categories.
- A new E2E test validating the feature end-to-end.

## Technical Implementation

### Files Modified

- `app/client/src/chart.ts` (new): Encapsulates all chart logic — `classifyColumns`, `pickDefaultAxes`, `coerceNumeric`, `buildChartData` (incl. pie "Other" grouping), `renderChart` (Chart.js lifecycle), and `buildChartControls` (controls UI).
- `app/client/src/main.ts`: Wires the Visualize button and chart panel into `displayResults()`, adds `toggleChartPanel()` and `resetChartPanel()`, and tracks the active Chart.js instance at module scope.
- `app/client/index.html`: Adds the hidden `#chart-container` with `#chart-controls`, a `.chart-canvas-wrapper`, and the `#chart-canvas` element.
- `app/client/src/style.css`: Styles for `.visualize-button`, `.chart-container`, `.chart-controls`, `.chart-control-group`, `.chart-canvas-wrapper` (min-height 300px), and `.chart-empty`.
- `app/client/src/types.d.ts`: Adds the `ChartType` union and `ColumnClassification` interface.
- `app/client/package.json`: Adds the `chart.js` (`^4.5.1`) dependency.
- `.claude/commands/e2e/test_chart_visualization.md` (new): E2E test file for the feature.

### Key Changes

- **Column classification by value inspection** — a column is numeric when ≥50% of its non-null values coerce to finite numbers (`NUMERIC_THRESHOLD`); everything else is categorical. This drives which columns each dropdown offers.
- **Numeric coercion guard** — `coerceNumeric()` returns `null` for null/undefined/empty strings and non-finite values; rows with a null Y value are dropped rather than charted as zero.
- **Chart.js instance lifecycle** — a module-level `activeChart` is destroyed before every re-render and reset on each new query, preventing "Canvas is already in use" errors and stale visuals.
- **Pie slice grouping** — pie charts with more than 15 categories keep the top 14 by value and sum the remainder into a single "Other" slice; tooltips show value plus percentage of total.
- **Zero-row safety** — the Export/Visualize button container is rebuilt only inside the `results.length > 0` branch, and the toggle button is re-attached standalone on error/zero-row results so the Visualize button never persists when there are no rows.

## How to Use

1. Run a natural-language query that returns rows with at least one text column and one numeric column.
2. In the results header, click the **📈 Visualize** button.
3. The chart panel appears below the results table with default axes pre-selected and a bar chart rendered.
4. Use the **Chart type** dropdown to switch between Bar, Line, and Pie.
5. Use the **X-axis** and **Y-axis** dropdowns to change which columns are plotted (Y-axis lists numeric columns only).
6. Hover over a data point or slice to see the exact value (pie slices also show a percentage).
7. Click **Visualize** again to hide the chart panel.

## Configuration

No configuration or environment variables are required. The feature adds the `chart.js` dependency (imported via `chart.js/auto`, which auto-registers all controllers and scales). Run `cd app/client && bun install` to install it.

## Testing

- `cd app/client && bun tsc --noEmit` — type-check with zero errors.
- `cd app/client && bun run build` — production build with zero errors.
- `cd app/server && uv run pytest` — confirm no server regressions (client-only change).
- Execute the E2E test `.claude/commands/e2e/test_chart_visualization.md` per `.claude/commands/test_e2e.md`: verifies the Visualize button appears only with rows, dropdowns are filtered correctly, and bar/pie charts render real, non-zero values.

## Notes

- New dependency: `chart.js` (`^4.5.1`). Chart.js bundles its own TypeScript types, so no `@types/chart.js` is needed.
- The implementation is intentionally client-only and function-based (no classes/decorators), consistent with the existing `main.ts` style — no server code was modified.
- The Product Inventory sample dataset (categorical name/category + numeric price/quantity) is a reliable dataset for exercising the feature.
