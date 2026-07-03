# E2E Test: Chart Visualization

Test the chart visualization feature in the Natural Language SQL Interface application.

## User Story

As a user of the Natural Language SQL Interface
I want to visualize my query results as bar, line, or pie charts
So that I can quickly understand trends and comparisons in my data without exporting it to another tool

## Test Steps

1. Navigate to the `Application URL`
2. Take a screenshot of the initial state
3. **Verify** the page title is "Natural Language SQL Interface"
4. **Verify** core UI elements are present:
   - Query input textbox
   - Query button
   - Upload Data button
   - Available Tables section

5. Click the "Upload" button to open the Upload modal
6. Click the "Product Inventory" sample data button (loads `products.csv` with categorical product columns and numeric price/quantity columns)
7. **Verify** a products table appears in the Available Tables section

8. Enter the query: "Show me all products with their prices"
9. Click the Query button
10. **Verify** the query results appear in a table with data
11. Take a screenshot of the results table

12. **Verify** the **Visualize** button is present in the results header (to the left of the Hide button)
13. Click the **Visualize** button
14. **Verify** the chart panel appears containing:
    - A chart-type selector (Bar / Line / Pie)
    - An X-axis dropdown
    - A Y-axis dropdown
    - A chart canvas
15. Take a screenshot of the rendered bar chart

16. **Verify** the Y-axis dropdown contains only numeric columns (e.g. price, quantity) and does NOT contain text columns (e.g. product name/category)
17. **Verify** the X-axis dropdown contains only text/categorical columns and does NOT contain the numeric price/quantity columns
18. **Verify** the bar chart canvas renders a non-empty chart — bars have visible height proportional to the data (not all zero / not a flat line). Confirm via the screenshot showing visible bars.

19. Change the chart-type selector to "Pie"
20. **Verify** the chart re-renders as a pie chart with proportional slices
21. Take a screenshot of the rendered pie chart

22. (Edge case) Enter a query that returns zero rows: "Show me all products with a price of -1"
23. Click the Query button
24. **Verify** the results show "No results found." and the **Visualize** button is NOT present

## Success Criteria
- The Visualize button appears in the results header only when there is at least one result row
- The Visualize button is hidden when the query returns zero rows
- Clicking Visualize reveals a chart panel with a chart-type selector, X-axis dropdown, and Y-axis dropdown
- The Y-axis dropdown offers only numeric columns; the X-axis dropdown offers only categorical/text columns
- The bar chart renders real, non-zero, proportional data values (not empty / flat / zero-height)
- Switching to a pie chart re-renders proportional slices correctly
- At least 4 screenshots are taken (initial state, results table, bar chart, pie chart)

## Output Format

```json
{
  "test_name": "Chart Visualization",
  "status": "passed|failed",
  "screenshots": [
    "<absolute path to codebase>/agents/<adw_id>/<agent_name>/img/chart_visualization/01_initial_state.png",
    "<absolute path to codebase>/agents/<adw_id>/<agent_name>/img/chart_visualization/02_results_table.png",
    "<absolute path to codebase>/agents/<adw_id>/<agent_name>/img/chart_visualization/03_bar_chart.png",
    "<absolute path to codebase>/agents/<adw_id>/<agent_name>/img/chart_visualization/04_pie_chart.png"
  ],
  "error": null
}
```
