# Patch: Fix X-axis dropdown to show only categorical columns

## Metadata
adw_id: `4`
review_change_request: `Issue #1: The X-axis dropdown is populated with all columns (both categorical and numeric) instead of only categorical/text columns. In the name+age query, 'age' (a numeric column) appears in the X-axis dropdown alongside 'name'. The spec's acceptance criteria explicitly states: 'X-axis only offers categorical/text columns'. The implementation uses [...categoricalColumns, ...numericColumns] for X-axis options instead of just categoricalColumns. Resolution: In initializeChartPanel(), change the X-axis dropdown population from const allXOptions = [...categoricalColumns, ...numericColumns] to const allXOptions = [...categoricalColumns] so only categorical columns are offered for the X-axis. Severity: blocker`

## Issue Summary
**Original Spec:** specs/issue-ec0b97a0-adw-4-sdlc_planner-add-chart-visualization.md
**Issue:** The X-axis dropdown in `initializeChartPanel()` includes numeric columns alongside categorical columns, violating the acceptance criteria that states "X-axis only offers categorical/text columns".
**Solution:** Change `const allXOptions = [...categoricalColumns, ...numericColumns]` to `const allXOptions = [...categoricalColumns]` on line 699 of `app/client/src/main.ts`.

## Files to Modify

- `app/client/src/main.ts` — Line 699: remove `...numericColumns` from `allXOptions` array

## Implementation Steps
IMPORTANT: Execute every step in order, top to bottom.

### Step 1: Fix X-axis dropdown population
- In `app/client/src/main.ts`, line 699, change `const allXOptions = [...categoricalColumns, ...numericColumns]` to `const allXOptions = [...categoricalColumns]`
- Update the comment on line 697 from "Populate X-axis dropdown with all columns (categorical first, then numeric)" to "Populate X-axis dropdown with categorical columns only"

## Validation
Execute every command to validate the patch is complete with zero regressions.

- `cd app/client && bun install` - Install dependencies
- `cd app/client && bun tsc --noEmit` - Run TypeScript type checking to validate no type errors
- `cd app/client && bun run build` - Run production build to validate bundling
- `cd app/server && uv run pytest` - Run server tests to validate zero regressions
- Read `.claude/commands/test_e2e.md`, then read and execute `.claude/commands/e2e/test_chart_visualization.md` E2E test to validate chart visualization works end-to-end

## Patch Scope
**Lines of code to change:** 2
**Risk level:** low
**Testing required:** TypeScript compilation, production build, server tests, E2E chart visualization test
