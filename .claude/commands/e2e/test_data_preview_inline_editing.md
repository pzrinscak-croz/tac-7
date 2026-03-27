# E2E Test: Data Preview with Inline Editing

Test data preview and inline editing functionality in the Natural Language SQL Interface application.

## User Story

As a data analyst
I want to click a table name to preview and edit its data inline
So that I can inspect, correct, and manage my data without writing SQL queries

## Test Steps

1. Navigate to the `Application URL`
2. Take a screenshot of the initial state
3. **Verify** a table exists in the Available Tables section (upload sample data if needed — click Upload, then click the "Users Data" sample button and wait for upload to complete)
4. **Verify** the table name has a pointer cursor (indicating it's clickable)
5. Click the table name to open the preview modal
6. Take a screenshot of the preview modal showing data with column headers
7. **Verify** the modal title shows "Preview: {tableName}"
8. **Verify** column headers are visible and data rows are displayed
9. **Verify** pagination shows "Page 1 of Y" where Y >= 1
10. Click a data cell to enter edit mode — **verify** an input appears with the current value
11. Type a new value and press Enter — **verify** the cell updates with the new value
12. Take a screenshot showing the edited cell
13. Click "Add Row" button — **verify** a new row with empty inputs appears at the top
14. Fill in values in the input fields and click Save — **verify** the row is inserted
15. Take a screenshot showing the new row
16. Click the Delete button (×) on a row — **verify** a confirmation dialog appears
17. Confirm the deletion — **verify** the row is removed from the table
18. Take a screenshot of the final state
19. Close the preview modal by clicking the × button
20. **Verify** the schema panel row count has updated to reflect the changes

## Success Criteria
- Clicking a table name opens the preview modal with correct data
- Column headers and data rows are displayed
- Pagination info is shown correctly
- Inline cell editing works (click to edit, Enter to save, Escape to cancel)
- Add Row inserts a new row that appears in the table
- Delete Row removes a row after confirmation
- Schema panel row count updates after mutations
- 5 screenshots are taken
