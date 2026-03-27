# Patch: Fix stale Visualize/Export buttons persisting on empty results

## Metadata
adw_id: `ec0b97a0`
review_change_request: `Issue #1: The Visualize button remains visible when a subsequent query returns 0 rows. The button container cleanup in displayResults() (lines 241-244 of main.ts) is inside the if (!response.error && response.results.length > 0) block, so it is never executed for empty results. The old Export, Visualize, and Hide buttons from the previous query persist in the DOM. Resolution: Move the existing button container cleanup to before the if block — remove any .results-header-buttons element unconditionally on every call to displayResults(), then only recreate it when results.length > 0.`

## Issue Summary
**Original Spec:** N/A
**Issue:** The `.results-header-buttons` container (containing Export, Visualize, and Hide buttons) is only cleaned up inside the `if (!response.error && response.results.length > 0)` block at line 238. When a query returns 0 rows or an error, the cleanup code at lines 241-244 is never reached, leaving stale buttons from a previous query visible in the DOM.
**Solution:** Move the button container removal (`querySelector('.results-header-buttons')?.remove()`) to execute unconditionally at the start of `displayResults()`, before the conditional block that creates new buttons. This ensures buttons are always cleared, and only recreated when there are actual results.

## Files to Modify

- `app/client/src/main.ts` — Move button container cleanup before the `if` guard

## Implementation Steps
IMPORTANT: Execute every step in order, top to bottom.

### Step 1: Remove the cleanup code from inside the `if` block
- In `app/client/src/main.ts`, remove lines 241-244 (the existing button container cleanup) from inside the `if (!response.error && response.results.length > 0)` block:
  ```
  // Remove existing button container if any
  const existingButtonContainer = resultsHeader.querySelector('.results-header-buttons');
  if (existingButtonContainer) {
    existingButtonContainer.remove();
  }
  ```

### Step 2: Add unconditional cleanup before the `if` block
- Insert the button container cleanup immediately before line 238 (`if (!response.error && response.results.length > 0)`), after the toggle button setup (line 235):
  ```typescript
  // Remove existing button container unconditionally
  const resultsHeader = document.querySelector('.results-header') as HTMLElement;
  const existingButtonContainer = resultsHeader?.querySelector('.results-header-buttons');
  if (existingButtonContainer) {
    existingButtonContainer.remove();
  }
  ```
- Update the `resultsHeader` declaration inside the `if` block (formerly line 239) to reuse the existing variable or re-query as needed, avoiding duplicate `const resultsHeader` declarations.

## Validation
Execute every command to validate the patch is complete with zero regressions.

1. `cd app/client && bun tsc --noEmit` — Verify no TypeScript type errors
2. `cd app/client && bun run build` — Verify frontend builds successfully

## Patch Scope
**Lines of code to change:** ~6
**Risk level:** low
**Testing required:** TypeScript check and frontend build; manual verification that buttons disappear on empty results and still appear on valid results
