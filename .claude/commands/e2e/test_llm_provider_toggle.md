# E2E Test: LLM Provider Toggle

Test the LLM provider dropdown in the Natural Language SQL Interface application.

## User Story

As a user
I want to pick the LLM provider in the UI and have my choice remembered
So that I can switch between OpenAI and Anthropic without code changes

## Test Steps

1. Navigate to the `Application URL`
2. Take a screenshot of the initial state
3. **Verify** the provider dropdown (`#llm-provider-select`) is visible in the query controls and defaults to `OpenAI`
4. Click the Upload button to open the upload modal
5. Click the "Users Data" sample button to load sample users data
6. **Verify** the modal closes and the `users` table appears in the Available Tables section
7. Change the provider dropdown to `Anthropic`
8. Take a screenshot showing the dropdown set to Anthropic
9. Reload the page
10. **Verify** the dropdown still shows `Anthropic` after reload (persistence via localStorage)
11. Take a screenshot of the page after reload
12. Enter the query "Show me all users from the users table" and click the Query button
13. **Verify** the results table appears and the SQL translation is displayed without errors
14. Take a screenshot of the Anthropic query results
15. Switch the provider dropdown back to `OpenAI`
16. Enter the query "Show me all users from the users table" and click the Query button
17. **Verify** the results table appears and the SQL translation is displayed without errors
18. Take a screenshot of the OpenAI query results

## Success Criteria
- The provider dropdown is visible in the query controls
- The dropdown defaults to `OpenAI` on first visit
- Selecting `Anthropic` and reloading preserves the `Anthropic` selection (localStorage persistence)
- A query executes successfully with the `Anthropic` selection
- A query executes successfully with the `OpenAI` selection
- 5 screenshots are saved
