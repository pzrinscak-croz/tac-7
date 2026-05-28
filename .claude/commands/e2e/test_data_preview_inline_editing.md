# E2E Test: Data Preview with Inline Editing

Test the data preview modal: open it from the schema panel, paginate, edit a cell, add a row, delete a row, and verify persistence across reloads.

## User Story

As a user of the Natural Language SQL Interface
I want to click a table name to preview, edit, add, and delete its rows in place
So that I can quickly correct data and inspect contents without writing SQL or using an external tool

## Test Steps

1. Navigate to the `Application URL`
2. Take a screenshot of the initial state
3. **Verify** the page title is "Natural Language SQL Interface"
4. **Verify** core UI elements are present:
   - Query input textbox
   - Query button
   - Upload Data button
   - Available Tables section

5. Click the "Upload" button to open the upload modal
6. Click the "Users Data" sample button (sample with 20 users)
7. **Verify** the `users` table appears in the Available Tables section
8. **Verify** the schema-panel row count shows `20 rows`
9. Take a screenshot of the schema panel with the `users` table loaded

10. Click the `users` table name (now rendered as a dotted-underlined clickable label) in the schema panel
11. **Verify** the preview modal opens with title text "Preview: users"
12. **Verify** the preview table has column headers matching the `users` columns
13. **Verify** the pagination indicator shows "Page 1 of 1" (20 rows fit on a single 50-row page)
14. Take a screenshot of the open preview modal

15. Click the first editable cell in the first row, clear its text, type `Edited Value`, then press `Enter`
16. **Verify** the cell text becomes `Edited Value` (commit succeeded; no error toast)
17. Take a screenshot of the edited cell

18. Click the `+ Add Row` button in the preview toolbar
19. **Verify** the row count in the underlying schema panel updates to `21 rows`
20. **Verify** a new (mostly empty) row is visible in the preview table
21. Take a screenshot of the newly added row

22. Click the `×` delete button on the newly added row (the last row in the preview)
23. Accept the confirmation dialog (`Delete this row? This cannot be undone.`)
24. **Verify** the row is removed from the preview
25. **Verify** the schema-panel row count returns to `20 rows`

26. Close the preview modal (click the `×` close button or the dark background outside the modal)
27. Reload the page
28. After reload, click the `users` table name again to re-open the preview
29. **Verify** the previously edited cell still shows `Edited Value` (proves persistence to SQLite)
30. Take a screenshot of the persisted edit

31. Close the preview modal

## Success Criteria

- Clicking a table name opens a preview modal showing column headers and rows (acceptance criterion #1)
- Pagination indicator "Page X of Y" displays correctly (acceptance criterion #2)
- Clicking a cell makes it editable; Enter commits; Escape would revert (acceptance criterion #3)
- The edited cell value persists after a page reload (acceptance criterion #4)
- The "Add Row" button inserts a visible new row that persists (acceptance criterion #5)
- The delete `×` button asks for confirmation and removes the row permanently (acceptance criterion #6)
- The schema-panel row count updates after add and delete (acceptance criterion #7)
- The existing `×` (remove table) button on the schema panel remains unaffected by the new click handler
- 5 screenshots are taken
