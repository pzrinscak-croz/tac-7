# E2E Test: Chart Visualization

Test chart visualization of query results in the Natural Language SQL Interface application.

## User Story

As a data analyst
I want to visualize my query results as a bar, line, or pie chart directly in the browser
So that I can quickly spot trends and comparisons without exporting the data to another tool

## Test Steps

1. Navigate to the `Application URL`
2. Take a screenshot of the initial state
3. **Verify** the page title is "Natural Language SQL Interface"
4. **Verify** core UI elements are present:
   - Query input textbox
   - Query button
   - Upload Data button
   - Available Tables section

5. Open the Upload modal and load the "Product Inventory" sample data (products.csv, which has a text name column and numeric price column)
6. **Verify** the products table appears in the Available Tables section

7. Enter the query: "Show all products with their prices"
8. Click the Query button
9. **Verify** the query results appear with multiple rows and at least one text column and one numeric column
10. **Verify** a "📈 Visualize" button appears in the results header (next to the Export and Hide buttons)
11. Take a screenshot of the results with the Visualize button

12. Click the "📈 Visualize" button
13. **Verify** a chart panel appears containing:
    - A Chart Type selector (Bar, Line, Pie)
    - An X-Axis dropdown
    - A Y-Axis dropdown
    - A chart canvas
14. **Verify** the Y-Axis dropdown contains a numeric column (e.g., price) and does NOT contain the text product name column
15. **Verify** the X-Axis dropdown contains the text product name column
16. Take a screenshot of the rendered bar chart
17. **Verify** the bar chart renders with non-zero bars. If feasible, use `browser_evaluate` to read the Chart.js instance data and assert the dataset contains finite, non-zero numeric values (not all zeros / not empty).

18. Change the Chart Type selector to "Pie"
19. **Verify** a pie chart renders with proportional slices and a visible legend
20. Take a screenshot of the pie chart

21. Run an empty-result query, e.g. "Show all products with a price greater than 999999999"
22. **Verify** the query returns 0 rows ("No results found.")
23. **Verify** the "📈 Visualize" button is NOT shown for the empty result
24. Take a screenshot of the empty-result state

## Success Criteria
- The Visualize button appears only for non-empty query results and is hidden for empty results
- The chart panel exposes a chart-type selector plus X and Y axis dropdowns
- The Y-Axis dropdown lists only numeric columns; the X-Axis dropdown lists categorical/text columns
- A bar chart renders with non-zero data values (bars have proportional heights)
- Switching to a pie chart renders proportional slices with a legend
- The chart canvas is at least 300px tall and readable
- 5 screenshots are taken (initial, results with Visualize button, bar chart, pie chart, empty-result state)

## Output Format

```json
{
  "test_name": "Chart Visualization",
  "status": "passed|failed",
  "screenshots": [
    "<absolute path to codebase>/agents/<adw_id>/<agent_name>/img/chart_visualization/01_initial_state.png",
    "<absolute path to codebase>/agents/<adw_id>/<agent_name>/img/chart_visualization/02_results_with_visualize_button.png",
    "<absolute path to codebase>/agents/<adw_id>/<agent_name>/img/chart_visualization/03_bar_chart.png",
    "<absolute path to codebase>/agents/<adw_id>/<agent_name>/img/chart_visualization/04_pie_chart.png",
    "<absolute path to codebase>/agents/<adw_id>/<agent_name>/img/chart_visualization/05_empty_result_no_visualize_button.png"
  ],
  "error": null
}
```
