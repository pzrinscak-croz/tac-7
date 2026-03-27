# E2E Test: Conversational Follow-ups

Test conversational follow-up functionality in the Natural Language SQL Interface application.

## User Story

As a data analyst
I want to ask follow-up questions that reference my previous query
So that I can iteratively explore data without re-specifying tables and conditions each time

## Test Steps

1. Navigate to the `Application URL`
2. Take a screenshot of the initial state
3. **Verify** the page title is "Natural Language SQL Interface"
4. Open the upload modal and load sample "Users Data"
5. **Verify** no context indicator (`#context-indicator`) is visible (should have `display: none`)
6. Enter and submit query: "Show me all users"
7. **Verify** results appear with SQL translation
8. Take a screenshot showing results
9. **Verify** context indicator appears with text containing "Continuing from: 'Show me all users'"
10. Take a screenshot showing the context indicator
11. Enter and submit follow-up query: "filter that by city = 'New York'"
12. **Verify** results appear and the SQL translation contains a WHERE clause referencing city
13. Take a screenshot of follow-up results
14. Click the "Clear context" button (`#clear-context-button`)
15. **Verify** context indicator disappears (`display: none`)
16. Take a screenshot showing context cleared

## Success Criteria
- Context indicator is visible after first successful query
- Follow-up query produces valid SQL without the user re-specifying the table
- "Clear context" button removes the context indicator
- Screenshots taken at each key step (initial state, first results, context indicator, follow-up results, context cleared)
