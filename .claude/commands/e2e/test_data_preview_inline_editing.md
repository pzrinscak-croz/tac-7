# E2E Test: Data Preview with Inline Editing

Test the table preview modal with inline cell editing, add/delete row, and pagination.

## User Story

As a data analyst working with uploaded CSV/JSON tables
I want to preview and edit table contents directly in the browser
So that I can fix typos, add missing rows, and clean up data without writing SQL by hand

## Test Steps

1. Navigate to the `Application URL`
2. Take a screenshot of the initial state
3. **Verify** the page title is "Natural Language SQL Interface"

4. Click the "Upload" button to open the upload modal
5. Click the "Users Data" sample button to load the `users` sample table
6. **Verify** the upload modal closes and a `users` table appears in the Available Tables list
7. **Verify** the `users` table row count chip shows a number greater than 0 (the users sample contains 20 rows)

8. **Verify** the table name "users" in the Available Tables list is rendered as a clickable element (cursor pointer / underlined-on-hover styling). Take a screenshot.

9. Click the "users" table name.
10. **Verify** a preview modal opens with the title "Preview: users".
11. **Verify** the modal shows the column headers from the `users` table.
12. **Verify** the modal body contains a table with multiple rows of data.
13. **Verify** each row has a "Delete" button in the last column. Take a screenshot of the open preview modal.

14. **Verify** the pagination label reads "Page 1 of 1" (since the 20-row sample fits on one page at limit=50).
15. **Verify** the "Prev" and "Next" buttons are both disabled.
16. **Verify** the "X rows total" status appears (e.g., "20 rows total"). Take a screenshot.

17. Click any cell in the first data row (e.g., the `name` column of the first row).
18. **Verify** the cell becomes an editable input prefilled with the current value.
19. Clear the input and type a new value (e.g., "EditedTestName") then press Enter.
20. **Verify** the cell updates to the new value "EditedTestName" and the input is gone. Take a screenshot.

21. Click the "+ Add Row" button.
22. **Verify** a new row appears in the table (likely at the end / on the last page).
23. **Verify** the "X rows total" status increments by 1 (e.g., "21 rows total"). Take a screenshot.
24. **Verify** the `users` table row count chip in the Available Tables list also reflects the new total (incremented by 1).

25. Close the preview modal (click the "×" button).
26. Re-open the preview by clicking the `users` table name again.
27. **Verify** the cell edit from step 20 is still present ("EditedTestName" appears in the data).
28. **Verify** the new row count is preserved (status shows the same total as in step 23).

29. Locate the newly-added row (it should have empty values in most cells). Click its "Delete" button.
30. **Verify** a browser confirmation dialog appears asking "Delete this row?". Accept the dialog.
31. **Verify** the row disappears from the table.
32. **Verify** the "X rows total" status decrements by 1 (back to original count, e.g., "20 rows total"). Take a screenshot.

33. Close the preview modal.
34. **Verify** the `users` table row count chip in the Available Tables list reflects the new total (back to 20).

## Success Criteria
- Table name in the Available Tables list is clickable and opens the preview modal
- Preview modal displays column headers and row data
- Pagination label and Prev/Next button disabled state are correct
- Inline cell editing works: Enter commits, value persists in DOM
- "+ Add Row" inserts a row, increments total, updates schema row count
- Edit and new row persist across modal close/open
- Delete confirms, removes the row, decrements total, updates schema row count
- 7 screenshots are taken
