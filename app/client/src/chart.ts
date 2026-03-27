import { Chart, registerables } from 'chart.js'

Chart.register(...registerables)

let currentChart: Chart | null = null

interface ColumnClassification {
  numeric: string[]
  text: string[]
}

/**
 * Classify columns as numeric or text by inspecting actual data values.
 * A column is numeric if every non-null value parses as a finite number.
 * Columns named 'id' or 'rowid' (case-insensitive) are excluded from numeric.
 */
export function classifyColumns(
  results: Record<string, any>[],
  columns: string[]
): ColumnClassification {
  const numeric: string[] = []
  const text: string[] = []

  for (const col of columns) {
    // Exclude id/rowid columns from numeric
    const lowerCol = col.toLowerCase()
    if (lowerCol === 'id' || lowerCol === 'rowid') {
      text.push(col)
      continue
    }

    const nonNullValues = results
      .map(row => row[col])
      .filter(v => v !== null && v !== undefined && v !== '')

    if (nonNullValues.length === 0) {
      text.push(col)
      continue
    }

    const allNumeric = nonNullValues.every(v => {
      const n = Number(v)
      return isFinite(n)
    })

    if (allNumeric) {
      numeric.push(col)
    } else {
      text.push(col)
    }
  }

  return { numeric, text }
}

/**
 * Create chart control elements (chart type selector, axis dropdowns).
 */
export function createChartControls(
  numericColumns: string[],
  textColumns: string[],
  onUpdate: (chartType: string, xColumn: string, yColumn: string) => void
): HTMLDivElement {
  const container = document.createElement('div')
  container.className = 'chart-controls'

  if (numericColumns.length === 0) {
    container.className = 'no-numeric-message'
    container.textContent = 'No numeric columns available for charting'
    return container
  }

  // Chart type selector
  const typeGroup = document.createElement('div')
  typeGroup.className = 'chart-control-group'
  const typeLabel = document.createElement('label')
  typeLabel.textContent = 'Chart Type'
  const typeSelect = document.createElement('select')
  typeSelect.className = 'chart-type-selector'
  for (const type of ['bar', 'line', 'pie']) {
    const option = document.createElement('option')
    option.value = type
    option.textContent = type.charAt(0).toUpperCase() + type.slice(1)
    typeSelect.appendChild(option)
  }
  typeGroup.appendChild(typeLabel)
  typeGroup.appendChild(typeSelect)

  // X-axis dropdown
  const xGroup = document.createElement('div')
  xGroup.className = 'chart-control-group'
  const xLabel = document.createElement('label')
  xLabel.textContent = 'X-Axis'
  const xSelect = document.createElement('select')
  xSelect.className = 'chart-axis-select'

  // If no text columns, use all columns (including numeric) for X
  const xColumns = textColumns.length > 0 ? textColumns : numericColumns
  for (const col of xColumns) {
    const option = document.createElement('option')
    option.value = col
    option.textContent = col
    xSelect.appendChild(option)
  }
  xGroup.appendChild(xLabel)
  xGroup.appendChild(xSelect)

  // Y-axis dropdown
  const yGroup = document.createElement('div')
  yGroup.className = 'chart-control-group'
  const yLabel = document.createElement('label')
  yLabel.textContent = 'Y-Axis'
  const ySelect = document.createElement('select')
  ySelect.className = 'chart-axis-select'
  for (const col of numericColumns) {
    const option = document.createElement('option')
    option.value = col
    option.textContent = col
    ySelect.appendChild(option)
  }
  yGroup.appendChild(yLabel)
  yGroup.appendChild(ySelect)

  container.appendChild(typeGroup)
  container.appendChild(xGroup)
  container.appendChild(yGroup)

  const fireUpdate = () => {
    onUpdate(typeSelect.value, xSelect.value, ySelect.value)
  }

  typeSelect.addEventListener('change', fireUpdate)
  xSelect.addEventListener('change', fireUpdate)
  ySelect.addEventListener('change', fireUpdate)

  return container
}

/**
 * Render a chart on the given canvas element.
 */
export function renderChart(
  canvas: HTMLCanvasElement,
  chartType: string,
  labels: string[],
  values: number[],
  xLabel: string,
  yLabel: string
): void {
  destroyChart()

  const colors = [
    '#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe',
    '#00f2fe', '#43e97b', '#fa709a', '#fee140', '#30cfd0',
    '#a18cd1', '#fbc2eb', '#ff9a9e', '#fecfef', '#ffecd2'
  ]

  let chartLabels = labels
  let chartValues = values

  // Pie chart: group slices beyond 15 into "Other"
  if (chartType === 'pie' && labels.length > 15) {
    const indexed = labels.map((label, i) => ({ label, value: values[i] }))
    indexed.sort((a, b) => b.value - a.value)
    const top14 = indexed.slice(0, 14)
    const otherSum = indexed.slice(14).reduce((sum, item) => sum + item.value, 0)
    chartLabels = [...top14.map(item => item.label), 'Other']
    chartValues = [...top14.map(item => item.value), otherSum]
  }

  const backgroundColors = chartLabels.map((_, i) => colors[i % colors.length])

  const datasets: any[] = [
    {
      label: yLabel,
      data: chartValues,
      backgroundColor:
        chartType === 'pie'
          ? backgroundColors
          : colors[0],
      borderColor:
        chartType === 'pie'
          ? backgroundColors.map(c => c)
          : colors[0],
      borderWidth: chartType === 'pie' ? 2 : 2,
      tension: 0.3,
    },
  ]

  const options: any = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: true,
        position: chartType === 'pie' ? 'right' : 'top',
      },
      tooltip: {
        callbacks: {
          label: (context: any) => {
            const val = context.parsed.y ?? context.parsed
            if (chartType === 'pie') {
              const total = chartValues.reduce((s, v) => s + v, 0)
              const pct = total > 0 ? ((context.parsed / total) * 100).toFixed(1) : '0'
              return `${context.label}: ${context.parsed} (${pct}%)`
            }
            return `${yLabel}: ${val}`
          },
        },
      },
    },
  }

  if (chartType !== 'pie') {
    options.scales = {
      x: {
        title: { display: true, text: xLabel },
      },
      y: {
        title: { display: true, text: yLabel },
        beginAtZero: true,
      },
    }
  }

  currentChart = new Chart(canvas, {
    type: chartType as any,
    data: {
      labels: chartLabels,
      datasets,
    },
    options,
  })
}

/**
 * Destroy the current chart instance to prevent memory leaks.
 */
export function destroyChart(): void {
  if (currentChart) {
    currentChart.destroy()
    currentChart = null
  }
}
