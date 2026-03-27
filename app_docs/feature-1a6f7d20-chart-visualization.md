# Chart Visualization

**ADW ID:** 1a6f7d20
**Date:** 2026-03-27
**Specification:** specs/issue-1a6f7d20-adw-23-sdlc_planner-add-chart-visualization.md

## Overview

Adds interactive chart visualization to the Natural Language SQL Interface. After a query returns results, a "Visualize" button appears in the results header allowing users to render data as bar, line, or pie charts using Chart.js. This is a client-only change that renders from the same `results[]` and `columns[]` data already returned by the query API.

## What Was Built

- New `chart.ts` module with column classification, chart controls creation, and Chart.js lifecycle management
- "Visualize" button added to the results header (alongside Export and Hide buttons)
- Chart type selector (Bar, Line, Pie)
- X-axis dropdown (categorical/text columns only)
- Y-axis dropdown (numeric columns only, excluding `id`/`rowid`)
- Auto-selection of sensible defaults (first text column for X, first numeric column for Y)
- Pie chart with "Other" grouping for datasets exceeding 15 categories
- Toggle behavior: clicking Visualize again hides the chart section
- Styles for chart container, controls, and canvas

## Technical Implementation

### Files Modified

- `app/client/package.json`: Added `chart.js` dependency
- `app/client/src/chart.ts`: New module — column classification, controls creation, chart rendering, destroy lifecycle
- `app/client/src/main.ts`: Integrated chart module into `displayResults()`; added Visualize button; cleans up chart on new queries
- `app/client/src/style.css`: Added styles for `.chart-section`, `.chart-controls`, `.chart-control-group`, `.chart-type-selector`, `.chart-axis-select`, `.chart-canvas-container`, `.visualize-button`, `.no-numeric-message`

### Key Changes

- **Column classification** (`classifyColumns`): A column is numeric if every non-null value parses as a finite number; columns named `id`/`rowid` (case-insensitive) are excluded from the numeric list and treated as text.
- **Chart controls** (`createChartControls`): Returns a DOM element with three selects (chart type, X-axis, Y-axis). If no numeric columns exist, returns a "No numeric columns available for charting" message instead.
- **Chart rendering** (`renderChart`): Destroys any existing Chart.js instance before creating a new one. Pie charts group slices beyond 15 into an "Other" category (sorted descending, top 14 kept). All Y-axis values are parsed via `Number()` before passing to Chart.js.
- **Cleanup** (`destroyChart`): Called at the start of `displayResults()` and when the Visualize button is toggled off, preventing memory leaks and rendering artifacts.
- **Integration in `main.ts`**: Visualize button only appears when `response.results.length > 0`. Clicking it toggles the `.chart-section` element appended after the results section.

## How to Use

1. Run a query in the Natural Language SQL Interface that returns at least one row.
2. Click the **📈 Visualize** button that appears in the results header.
3. Chart controls appear: select a **Chart Type** (Bar, Line, or Pie), an **X-Axis** column (categorical), and a **Y-Axis** column (numeric).
4. The chart renders automatically and updates whenever a control changes.
5. Click **📈 Visualize** again to hide the chart.
6. Running a new query automatically removes the previous chart.

## Configuration

No configuration required. Chart.js is bundled as a client dependency via `chart.js` (v4.x). No backend changes needed.

## Testing

- TypeScript type check: `cd app/client && bun tsc --noEmit`
- Production build: `cd app/client && bun run build`
- Server regression tests: `cd app/server && uv run pytest`
- E2E: run the `test_chart_visualization` E2E test (see `.claude/commands/e2e/test_chart_visualization.md`)

## Notes

- **Edge cases handled**: 0-row results (Visualize button hidden), all-text columns (no-numeric message), null values (skipped during classification), mixed-type columns (classified as text), pie charts with >15 categories ("Other" grouping), only-numeric columns (X-axis falls back to numeric columns).
- **Canvas lifecycle**: Chart.js requires `.destroy()` before re-rendering on the same canvas element. `destroyChart()` is called before every new render and when the chart section is removed.
- **No backend changes**: The feature is entirely client-side, reusing the existing `QueryResponse.results` and `QueryResponse.columns` fields.
