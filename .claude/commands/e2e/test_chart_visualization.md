# E2E Test: Chart Visualization

Test chart visualization functionality in the Natural Language SQL Interface application.

## User Story

As a data analyst
I want to visualize query results as interactive charts
So that I can quickly understand data patterns and share insights with stakeholders

## Test Steps

1. Navigate to the `Application URL`
2. Take a screenshot of the initial state
3. **Verify** the page title is "Natural Language SQL Interface"
4. **Verify** core UI elements are present:
   - Query input textbox
   - Query button
   - Upload Data button
   - Available Tables section

5. Upload a test CSV file containing sample data with numeric columns (e.g., products with prices/quantities)
6. **Verify** the table appears in the Available Tables section
7. Take a screenshot of the table with columns visible

8. Enter a query: "SELECT category, price FROM uploaded_table LIMIT 10"
9. Click the Query button
10. **Verify** the query results appear
11. **Verify** a "Visualize" button appears to the right of Export button
12. Take a screenshot of query results with visualize button

13. Click the Visualize button
14. **Verify** a chart modal opens with:
    - Chart type selector (bar, line, pie)
    - X-Axis dropdown (categorical/text columns)
    - Y-Axis dropdown (numeric columns)
    - Generate Chart button
15. **Verify** sensible defaults are auto-selected (first text column for X, first numeric for Y)
16. Take a screenshot of chart modal

17. Leave chart type as Bar and click Generate Chart
18. **Verify** a bar chart renders with:
    - Bars proportional to data values
    - Y-axis starting at 0 with auto-scaling
    - Tooltips showing exact values on hover
    - Legend visible
    - Axis labels showing column names
19. Take a screenshot of bar chart

20. Change chart type to Line and click Generate Chart
21. **Verify** a line chart renders with:
    - Line connecting data points
    - Y-axis starting at 0
    - Filled area under line
    - Same data as bar chart
22. Take a screenshot of line chart

23. Change chart type to Pie and click Generate Chart
24. **Verify** a pie chart renders with:
    - Slices proportional to values
    - Percentage labels in tooltips
    - Legend on the right side
25. Take a screenshot of pie chart

26. Close the modal

27. **Edge Case: 0 rows** - Run query "SELECT * FROM uploaded_table WHERE 1=0"
28. **Verify** the Visualize button is NOT shown for 0-row results
29. Take a screenshot showing no visualize button

30. **Edge Case: No numeric columns** - Run query "SELECT category, name FROM uploaded_table LIMIT 10" (only text columns)
31. **Verify** the Visualize button is NOT shown (no numeric data available)
32. Take a screenshot

33. Run a query with numeric data to show Visualize button again
34. **Verify** Visualize button appears

35. Open Visualize modal and change X-Axis to a numeric column
36. **Verify** the chart type selector dropdown shows all chart types
37. Take a screenshot of axis selection

38. Close the modal
39. Take a final screenshot

## Success Criteria
- Visualize button appears after query with results containing rows
- Visualize button is hidden for 0-row results
- Visualize button is hidden when no numeric columns available
- Chart type selector works (bar/line/pie)
- X-axis dropdown only shows text/categorical columns
- Y-axis dropdown only shows numeric columns (excludes id/rowid)
- Auto-selection chooses sensible defaults
- Bar chart bars have proportional heights, Y-axis auto-scales
- Pie chart slices proportional with percentage tooltips
- Pie chart limits to 15 slices with "Other" grouping (if applicable)
- All Y values parsed as numbers before charting
- Tooltips show exact values on hover
- Legend and axis labels visible
- Chart has minimum 300px height
- All 8+ screenshots are taken documenting the feature