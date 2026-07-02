# Chart Visualization of Query Results

**ADW ID:** b4247189
**Date:** 2026-07-03
**Specification:** specs/issue-46-adw-b4247189-sdlc_planner-add-chart-visualization.md

## Overview

Adds a client-side chart visualization feature to the Natural Language SQL Interface. After a query returns rows, a **📈 Visualize** button appears in the results header; clicking it opens a panel where the user picks a chart type (bar, line, or pie) and which columns map to the X and Y axes, then renders the data with [Chart.js](https://www.chartjs.org/). The feature is entirely client-side and works from the data already held in the results table — no backend changes.

## What Was Built

- A **Visualize** button in the results header, shown only for non-empty results (hidden when 0 rows).
- A collapsible chart panel with a chart-type selector (Bar / Line / Pie) and X-axis / Y-axis dropdowns.
- Data-driven column classification that inspects actual values (not SQL metadata) to split columns into numeric vs. categorical.
- Type-aware dropdowns: Y-axis offers only numeric columns; X-axis offers only categorical/text columns.
- Sensible auto-defaults: first text column for X, first non-`id`/`rowid` numeric column for Y.
- Robust numeric parsing (`parseNumericValue`) that strips currency symbols and thousands separators so string-stored numbers chart correctly.
- Bar/line charts with auto-scaling, zero-based Y axis, axis titles, legend, and tooltips.
- Pie charts with per-label aggregation, a 15-slice cap (remainder grouped as "Other"), and percentage tooltips.
- A "No numeric columns available" empty state instead of rendering an empty chart.
- Clean chart lifecycle management (destroy/recreate) to avoid canvas-reuse errors and stale charts across queries.
- A new E2E test covering the full flow.

## Technical Implementation

### Files Modified

- `app/client/package.json`: Added `chart.js` (`^4.5.1`) as a runtime dependency.
- `app/client/src/types.d.ts`: Added `type ChartKind = 'bar' | 'line' | 'pie'` and `interface ClassifiedColumns { numeric: string[]; categorical: string[] }`.
- `app/client/src/main.ts`: Core implementation (~360 lines added). Registers Chart.js `registerables`; adds the Visualize button in `displayResults()`; adds helpers `parseNumericValue`, `classifyColumns`, `pickDefaultX`, `pickDefaultY`, `buildChartPanel`, `createLabeledSelect`, `renderChart`, `pieColor`, plus `destroyChart`/`removeChartPanel` for lifecycle management.
- `app/client/src/style.css`: New styles for `.visualize-button`, `.chart-panel`, `.chart-controls`, `.chart-control`, `.chart-select`, `.chart-canvas-container` (min 300px / 360px height), and `.chart-no-data`, all reusing existing CSS variables.
- `.claude/commands/e2e/test_chart_visualization.md`: New E2E test validating the feature end-to-end.

### Key Changes

- **Classify from data, not schema:** the `/api/query` response only provides `columns` and `results` (no per-column SQL types), so a column is treated as numeric only when it has at least one value and every non-null value parses to a finite number (sampled up to 500 rows for large result sets).
- **Numeric coercion before charting:** all Y values pass through `parseNumericValue` before reaching Chart.js; rows whose Y is not a finite number are dropped, preventing empty/flat/zero-height charts.
- **Single module-scoped Chart instance:** `chartInstance` is destroyed before every re-render, panel rebuild, and new query, avoiding "Canvas is already in use" errors.
- **Panel reset per query:** `displayResults()` calls `removeChartPanel()` and removes any stale Visualize button so previous charts never linger. Because the button is created only in the non-empty branch, it is inherently hidden for 0-row results.
- **Pie aggregation & capping:** pie values are summed per X label, sorted descending, capped at 15 slices with the remainder grouped into "Other", with tooltips showing exact value and percentage.
- **Fill-the-container sizing:** charts use `responsive: true` + `maintainAspectRatio: false` inside a fixed-height (≥300px) `position: relative` container for readability without scrolling.

## How to Use

1. Run a natural-language query that returns rows with at least one numeric and one text column (e.g., "Show all products with their prices").
2. In the results header, click the **📈 Visualize** button.
3. In the chart panel, choose a **Chart Type** (Bar, Line, or Pie).
4. Select the **X-Axis** (categorical column) and **Y-Axis** (numeric column); sensible defaults are pre-selected.
5. Hover data points/slices to see exact values (and percentages for pie). Click **Visualize** again to hide the panel.

## Configuration

No configuration required. The only new dependency is `chart.js` (client-side, tree-shakeable). Run `cd app/client && bun install` to install it.

## Testing

- Type-check: `cd app/client && bun tsc --noEmit`
- Build: `cd app/client && bun run build`
- Server regression: `cd app/server && uv run pytest` (feature is client-only; should pass unchanged)
- E2E: read `.claude/commands/test_e2e.md`, then run `.claude/commands/e2e/test_chart_visualization.md` — verifies the Visualize button appears for non-empty results, dropdowns are correctly typed, bar/line/pie charts render real values, and the button is hidden for empty results.

## Notes

- Column classification and numeric parsing are pure functions (`classifyColumns`, `parseNumericValue`), making the correctness core easy to reason about and unit-test later.
- Edge cases handled: string-stored numbers (e.g., `"$1,200.00"`), null values within numeric columns (row dropped, column stays numeric), only `id`/`rowid` numeric columns (falls back to first numeric), >15 pie categories ("Other" grouping), duplicate pie labels (summed), and repeated chart-type/axis switching (no canvas-reuse errors).
- Implementation stays in the existing vanilla-TS, function-based, imperative-DOM style of `main.ts` — no frameworks or decorators.
- Future considerations (out of scope): multi-series support, downloadable chart images (`toBase64Image`), and remembering the last-used chart type.
