# E2E Test: Conversational Follow-ups

Test that conversational context carries forward between queries in the Natural Language SQL Interface application.

## User Story

As a data analyst
I want each follow-up query to remember my previous question and its SQL
So that I can iteratively refine results without repeating the full context each time

## Test Steps

1. Navigate to the `Application URL`
2. Take a screenshot of the initial state
3. **Verify** the page title is "Natural Language SQL Interface"
4. Open the Upload modal by clicking the "Upload" button
5. Load the "Users Data" sample by clicking the sample button labeled "Users Data"
6. **Verify** the modal closes and a `users` table appears in the Available Tables section
7. Inspect the `users` table columns; note whether a city-like column exists. If no `city` column is present, choose an existing column (e.g. an id or name column) and a plausible value for the follow-up filter in step 12.

8. Enter the query: "show all users"
9. Click the Query button
10. **Verify** the query results appear and the SQL translation is displayed (should contain "FROM users")
11. **Verify** a context indicator with the text "Continuing from: 'show all users'" and a "Clear context" button are visible
12. Take a screenshot of the context indicator

13. Enter a follow-up query: "filter that by city = 'New York'" (or, if no city column exists, an equivalent filter on an existing column such as "filter that where <column> = <value>")
14. Click the Query button
15. **Verify** the query results/SQL appear and the generated SQL references the `users` table (contains "FROM users") even though the follow-up query did not re-specify the table
16. Take a screenshot of the follow-up SQL translation

17. Click the "Clear context" button
18. **Verify** the "Continuing from: ..." context indicator is no longer visible

19. Open the Upload modal again by clicking "Upload"
20. Load a different sample dataset (e.g. "Product Inventory")
21. **Verify** the modal closes and the context indicator is absent (no "Continuing from: ..." label)
22. Take a screenshot showing the cleared context after upload

## Success Criteria
- The context indicator "Continuing from: 'show all users'" appears after the first successful query
- The follow-up query produces SQL referencing the `users` table without the query re-specifying it
- Clicking "Clear context" hides the context indicator
- Loading a new sample dataset clears the context indicator
- At least 4 screenshots are taken (initial state, context indicator, follow-up SQL, cleared context after upload)
