# E2E Test: Conversational Follow-ups

Test conversational follow-up context in the Natural Language SQL Interface application. After a successful query, the previous question + SQL are automatically carried forward so the next query can be interpreted as a follow-up.

## User Story

As a user querying my data with natural language
I want the app to remember my previous question and its SQL so I can ask follow-ups like "filter that by city"
So that I can iteratively refine results without re-specifying tables and columns

## Test Steps

1. Navigate to the `Application URL`
2. Take a screenshot of the initial state
3. Click the "Upload" button to open the Upload modal
4. Click the "Users Data" sample button to load the sample `users` table
5. **Verify** the modal closes and the `users` table appears in the Available Tables section
6. Take a screenshot of the loaded table

7. Enter the query: "show all users"
8. Click the Query button
9. **Verify** the query results appear and the SQL translation contains "FROM users"
10. **Verify** the context indicator is now visible and shows the label "Continuing from: 'show all users'"
11. Take a screenshot of the results with the context indicator visible

12. Enter the follow-up query: "filter that by city = 'New York'"
13. Click the Query button
14. **Verify** the results appear and the generated SQL references the `users` table (contains "FROM users") WITHOUT the user re-specifying the table
15. **Verify** the generated SQL contains a `city` filter (e.g. "city" and "New York")
16. Take a screenshot of the follow-up SQL

17. Click the "Clear context" button
18. **Verify** the context indicator label disappears (context indicator is hidden)
19. Take a screenshot showing the context indicator is gone

## Success Criteria
- Sample users data loads successfully
- First query "show all users" produces SQL containing "FROM users"
- The "Continuing from: 'show all users'" label becomes visible after the first query
- The follow-up query produces SQL that references the `users` table and filters by city without re-specifying the table
- Clicking "Clear context" hides the context indicator label
- 5 screenshots are taken

## Output Format

```json
{
  "test_name": "Conversational Follow-ups",
  "status": "passed|failed",
  "screenshots": [
    "<absolute path to codebase>/agents/<adw_id>/<agent_name>/img/conversational_followups/01_initial_state.png",
    "<absolute path to codebase>/agents/<adw_id>/<agent_name>/img/conversational_followups/02_users_loaded.png",
    "<absolute path to codebase>/agents/<adw_id>/<agent_name>/img/conversational_followups/03_first_query_context_visible.png",
    "<absolute path to codebase>/agents/<adw_id>/<agent_name>/img/conversational_followups/04_followup_sql.png",
    "<absolute path to codebase>/agents/<adw_id>/<agent_name>/img/conversational_followups/05_context_cleared.png"
  ],
  "error": null
}
```
