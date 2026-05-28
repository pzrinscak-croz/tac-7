# E2E Test: Chart Visualization

Test client-side chart visualization of query results in the Natural Language SQL Interface application.

## User Story

As a data analyst
I want to visualize query results as a bar, line, or pie chart with one click
So that I can spot trends and shapes in the data without exporting to a separate tool

## Test Steps

1. Navigate to the `Application URL`
2. Take a screenshot of the initial state
3. **Verify** the page title is "Natural Language SQL Interface"
4. **Verify** core UI elements are present:
   - Query input textbox
   - Query button
   - Upload Data button
   - Available Tables section

5. Click the Upload Data button to open the upload modal
6. Click the "Product Inventory" sample data button to load the `products` table
7. **Verify** the `products` table appears in the Available Tables section

8. Enter the query: "Show product name and price from products"
9. Click the Query button
10. **Verify** the query results appear with multiple rows including a text column (e.g. `name`) and a numeric column (e.g. `price`)
11. **Verify** a button with text "📈 Visualize" appears in the results header, positioned to the left of the "Export" / "📊 CSV Export" button
12. Take a screenshot of the results header showing the Visualize, Export, and Hide buttons

13. Click the Visualize button
14. **Verify** a chart panel becomes visible directly below the results table
15. **Verify** the chart panel contains:
    - A chart-type `<select>` with options Bar, Line, Pie
    - An X-axis `<select>`
    - A Y-axis `<select>`
    - A `<canvas>` element rendering inside a wrapper at least 300px tall
16. **Verify** the default Y axis selection is a numeric column that is NOT `id` or `rowid` (e.g. `price`)
17. **Verify** the default X axis selection is a text/categorical column (e.g. `name`)
18. **Verify** the Y-axis `<select>` does NOT contain an `<option>` whose value equals the text column (e.g. no `name` option in Y)
19. Take a screenshot of the rendered bar chart

20. Use `mcp__playwright__browser_evaluate` to read the Chart.js instance's dataset values via `document.querySelector('.chart-canvas-wrapper canvas')` and verify:
    - The chart instance exists (e.g. via `Chart.getChart(canvas)` from `chart.js`)
    - All Y values used are finite numbers (not NaN, not strings)
    - At least one value is strictly greater than 0 — confirming the bars are non-zero height
21. Take a screenshot demonstrating bars with visible non-zero heights

22. Change the chart-type `<select>` to "Pie"
23. **Verify** the chart canvas re-renders without console errors and without a Chart.js "Canvas is already in use" error
24. Take a screenshot of the pie chart

25. Change the chart-type `<select>` to "Line"
26. **Verify** the chart canvas re-renders cleanly into a line chart
27. Take a screenshot of the line chart

28. Enter a query that returns zero rows: "SELECT * FROM products WHERE 1=0"
29. Click the Query button
30. **Verify** the results section shows "No results found." (or equivalent empty-state)
31. **Verify** the Visualize button is NOT rendered in the results header
32. Take a screenshot of the empty-results state with the Visualize button absent

## Success Criteria
- Visualize button appears in the results header to the left of Export when there is at least one row
- Visualize button is absent when the query returns zero rows
- Chart panel shows chart-type, X-axis, and Y-axis selectors plus a canvas at least 300px tall
- Y-axis dropdown lists only numeric columns (excluding `id` / `rowid`)
- X-axis dropdown lists only categorical/text columns (falling back to numeric when none exist)
- Default X is a text column and default Y is a non-`id` numeric column
- Bar chart renders bars with non-zero height (all Y values are finite numbers)
- Switching chart type to Pie and back to Line re-renders without "Canvas is already in use" errors
- 5+ screenshots are taken
