# E2E Test: Chart Visualization

Test interactive chart visualization (bar / line / pie) of query results.

## User Story

As a data analyst
I want to visualize query results as bar, line, or pie charts directly in the browser
So that I can quickly spot trends, comparisons, and distributions without exporting

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
6. Click the "Product Inventory" sample button (loads products.csv with text + numeric columns)
7. **Verify** the modal closes and a `products` table appears

8. Enter the query: "Show me all products" (or "SELECT * FROM products LIMIT 10")
9. Click the Query button
10. **Verify** the query results table appears with at least one row
11. **Verify** the Visualize button is present in the results header buttons
12. Take a screenshot of the results with the Visualize button visible

13. Click the Visualize button
14. **Verify** the visualization panel appears with:
    - Chart-type selector (Bar, Line, Pie)
    - X-axis and Y-axis selects
    - A canvas (#chart-canvas)
15. **Verify** the Y-axis select contains a numeric column (price/quantity) and not a pure text column (name/category)
16. **Verify** (via evaluate) #chart-canvas has non-zero clientWidth and clientHeight
17. Take a screenshot of the bar chart

18. Click "Line"
19. **Verify** the chart re-renders without console errors
20. Take a screenshot of the line chart

21. Click "Pie"
22. **Verify** the chart re-renders without console errors
23. Take a screenshot of the pie chart

24. Run a query returning 0 rows: SELECT * FROM products WHERE 1=0
25. **Verify** the results indicate no results
26. **Verify** the Visualize button is NOT present
27. Take a final screenshot

## Success Criteria
- Visualize button appears for non-empty results, hidden for empty results
- Clicking Visualize reveals chart-type selector, X/Y selects, canvas
- Y-axis only offers numeric columns
- Bar, Line, Pie all render
- Canvas has non-zero size
- No console errors
- At least 5 screenshots taken
