# Patch: Fix CSV export button text in query results section

## Metadata
adw_id: `Issue`
review_change_request: `Issue #9: "CSV" texts dont match - Under available tables section the csv export button has the correct text "in CSV". Update the query result section csv export button text should match this.`

## Issue Summary
**Original Spec:**
**Issue:** The query results section export button displays "📊 CSV Export" (getDownloadIcon() + " Export"), while the available tables section export button correctly displays just "📊 CSV" (getDownloadIcon() only). The texts don't match.
**Solution:** Remove the " Export" suffix from the query results export button so it matches the available tables section button text.

## Files to Modify
- `app/client/src/main.ts`

## Implementation Steps

### Step 1: Update query results export button text
- In `app/client/src/main.ts` at line 242, change:
  ```ts
  exportButton.innerHTML = `${getDownloadIcon()} Export`;
  ```
  to:
  ```ts
  exportButton.innerHTML = getDownloadIcon();
  ```

## Validation
1. Start the app and verify the query results export button now shows "📊 CSV" instead of "📊 CSV Export"
2. Verify the available tables export button still shows "📊 CSV"
3. Verify both buttons function correctly (export works)

## Patch Scope
**Lines of code to change:** 1
**Risk level:** low
**Testing required:** Visual check that both CSV export buttons display identical text
