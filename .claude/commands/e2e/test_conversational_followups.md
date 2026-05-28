# E2E Test: Conversational Follow-ups

Test single-turn conversational follow-up context in the Natural Language SQL Interface application.

## User Story

As a user querying my data in natural language
I want my follow-up questions to inherit the context of the previous query
So that I can iteratively refine results ("now filter by city") without restating the table name or original question.

## Test Steps

1. Navigate to the `Application URL`
2. Take a screenshot of the initial state
3. **Verify** the "Continuing from" context pill is NOT visible at start
4. Click the Upload Data button to open the upload modal
5. Click the "Users Data" sample button to load the users sample dataset
6. **Verify** the modal closes and the `users` table appears in the Available Tables list

7. Enter the query: "Show me all users"
8. Click the Query button
9. **Verify** the query results appear
10. **Verify** the SQL translation contains the table reference `users`
11. Take a screenshot of the initial query results
12. **Verify** the "Continuing from:" context pill is now visible above the query input and contains the text `Show me all users`

13. Enter the follow-up query: "filter that by city"
14. Click the Query button
15. **Verify** the new query results appear
16. **Verify** the generated SQL contains the table reference `users` AND the keyword `WHERE` AND the column `city` (all case-insensitive). The specific city value the LLM picks is not asserted — only that the SQL references the `users` table and filters by `city`.
17. Take a screenshot of the follow-up SQL and results
18. **Verify** the "Continuing from:" context pill is still visible and now reflects the latest successful query (`filter that by city`)

19. Click the "×" Clear context button on the pill
20. **Verify** the "Continuing from" context pill is hidden
21. Take a screenshot of the final state with the pill cleared

## Success Criteria
- The "Continuing from" pill is hidden when no context is active
- The pill becomes visible after the first successful query and shows the previous natural language query
- The follow-up query generates SQL that references the original `users` table without the user restating it (the conversational follow-up context works)
- The pill updates to reflect the most recent successful query
- The Clear context button hides the pill
- 4 screenshots are taken
