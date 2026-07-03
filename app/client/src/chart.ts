import Chart from 'chart.js/auto';

// Maximum number of pie slices before grouping the remainder into "Other".
const MAX_PIE_SLICES = 15;

// A column is considered numeric when this fraction (or more) of its
// non-null values coerce to finite numbers.
const NUMERIC_THRESHOLD = 0.5;

// Palette used for pie chart slices and bar/line accents.
const PALETTE = [
  '#667eea', '#764ba2', '#28a745', '#dc3545', '#fd7e14',
  '#17a2b8', '#ffc107', '#e83e8c', '#20c997', '#6f42c1',
  '#007bff', '#6610f2', '#f4a261', '#2a9d8f', '#e76f51',
  '#adb5bd',
];

/**
 * Coerce a value to a finite number, returning null when it is not numeric.
 * Empty strings and null/undefined are treated as non-numeric.
 */
export function coerceNumeric(value: any): number | null {
  if (value === null || value === undefined) return null;
  if (typeof value === 'string' && value.trim() === '') return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

/**
 * Classify each column as numeric or categorical by inspecting the actual
 * result values. A column is numeric when the majority of its non-null values
 * coerce to finite numbers; everything else is categorical.
 */
export function classifyColumns(
  results: Record<string, any>[],
  columns: string[]
): ColumnClassification {
  const numeric: string[] = [];
  const categorical: string[] = [];

  columns.forEach((col) => {
    let nonNull = 0;
    let numericCount = 0;

    results.forEach((row) => {
      const value = row[col];
      if (value === null || value === undefined || (typeof value === 'string' && value.trim() === '')) {
        return;
      }
      nonNull += 1;
      if (coerceNumeric(value) !== null) {
        numericCount += 1;
      }
    });

    if (nonNull > 0 && numericCount / nonNull >= NUMERIC_THRESHOLD) {
      numeric.push(col);
    } else {
      categorical.push(col);
    }
  });

  return { numeric, categorical };
}

/**
 * Pick sensible default axes:
 *  - X: first categorical column (fallback: first column overall).
 *  - Y: first numeric column whose name is not id/rowid (fallback: first numeric).
 */
export function pickDefaultAxes(
  classification: ColumnClassification,
  columns: string[]
): { xCol: string; yCol: string } {
  const { numeric, categorical } = classification;

  const xCol = categorical.length > 0 ? categorical[0] : columns[0];

  const preferredY = numeric.find((col) => {
    const lower = col.toLowerCase();
    return lower !== 'id' && lower !== 'rowid';
  });
  const yCol = preferredY ?? numeric[0];

  return { xCol, yCol };
}

interface ChartData {
  labels: string[];
  values: number[];
}

/**
 * Build chart-ready labels and numeric values from the results.
 * Y values are coerced to numbers, dropping rows whose Y value is not numeric.
 * For pie charts with more than MAX_PIE_SLICES categories, the smallest
 * remaining categories are summed into a single "Other" slice.
 */
export function buildChartData(
  results: Record<string, any>[],
  xCol: string,
  yCol: string,
  chartType: ChartType
): ChartData {
  const labels: string[] = [];
  const values: number[] = [];

  results.forEach((row) => {
    const y = coerceNumeric(row[yCol]);
    if (y === null) return;
    const rawX = row[xCol];
    labels.push(rawX === null || rawX === undefined ? '' : String(rawX));
    values.push(y);
  });

  if (chartType === 'pie' && labels.length > MAX_PIE_SLICES) {
    // Keep the top (MAX_PIE_SLICES - 1) by value, group the rest into "Other".
    const indexed = values.map((value, index) => ({ label: labels[index], value }));
    indexed.sort((a, b) => b.value - a.value);

    const keep = indexed.slice(0, MAX_PIE_SLICES - 1);
    const rest = indexed.slice(MAX_PIE_SLICES - 1);
    const otherTotal = rest.reduce((sum, item) => sum + item.value, 0);

    const groupedLabels = keep.map((item) => item.label);
    const groupedValues = keep.map((item) => item.value);
    groupedLabels.push('Other');
    groupedValues.push(otherTotal);

    return { labels: groupedLabels, values: groupedValues };
  }

  return { labels, values };
}

/**
 * Render (or re-render) a Chart.js chart onto the given canvas.
 * Destroys any previous chart instance first to avoid canvas-reuse errors.
 * Returns the newly created Chart instance.
 */
export function renderChart(
  canvas: HTMLCanvasElement,
  results: Record<string, any>[],
  xCol: string,
  yCol: string,
  chartType: ChartType,
  prevChart: Chart | null
): Chart {
  if (prevChart) {
    prevChart.destroy();
  }

  const { labels, values } = buildChartData(results, xCol, yCol, chartType);

  const isCircular = chartType === 'pie';
  const backgroundColor = isCircular
    ? labels.map((_, i) => PALETTE[i % PALETTE.length])
    : 'rgba(102, 126, 234, 0.6)';
  const borderColor = isCircular
    ? labels.map((_, i) => PALETTE[i % PALETTE.length])
    : '#667eea';

  const chart = new Chart(canvas, {
    type: chartType,
    data: {
      labels,
      datasets: [
        {
          label: yCol,
          data: values,
          backgroundColor,
          borderColor,
          borderWidth: chartType === 'line' ? 2 : 1,
          fill: false,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: true,
          position: isCircular ? 'right' : 'top',
        },
        tooltip: {
          callbacks: {
            label: (context) => {
              const value = context.parsed;
              if (isCircular) {
                const total = values.reduce((sum, v) => sum + v, 0);
                const numeric = typeof value === 'number' ? value : (value as any).y ?? 0;
                const pct = total > 0 ? ((numeric / total) * 100).toFixed(1) : '0.0';
                return `${context.label}: ${numeric} (${pct}%)`;
              }
              const numeric = typeof value === 'number' ? value : (value as any).y ?? 0;
              return `${yCol}: ${numeric}`;
            },
          },
        },
      },
      scales: isCircular
        ? {}
        : {
            x: {
              title: { display: true, text: xCol },
            },
            y: {
              beginAtZero: true,
              title: { display: true, text: yCol },
            },
          },
    },
  });

  return chart;
}

/**
 * Build the chart controls UI (chart-type selector + X/Y axis dropdowns) into
 * the given container. If there are no numeric columns, renders a
 * "No numeric columns available" message and returns null.
 *
 * The onChange callback is invoked with the current selection whenever the
 * chart type or an axis changes, and once initially with the defaults.
 */
export function buildChartControls(
  container: HTMLElement,
  results: Record<string, any>[],
  columns: string[],
  onChange: (chartType: ChartType, xCol: string, yCol: string) => void
): boolean {
  container.innerHTML = '';

  const classification = classifyColumns(results, columns);

  if (classification.numeric.length === 0) {
    const empty = document.createElement('div');
    empty.className = 'chart-empty';
    empty.textContent = 'No numeric columns available';
    container.appendChild(empty);
    return false;
  }

  const { xCol: defaultX, yCol: defaultY } = pickDefaultAxes(classification, columns);

  // X-axis candidates: categorical columns (fallback to all columns if none).
  const xOptions = classification.categorical.length > 0 ? classification.categorical : columns;

  const typeSelect = createSelect(
    'chart-type-select',
    [
      { value: 'bar', label: 'Bar' },
      { value: 'line', label: 'Line' },
      { value: 'pie', label: 'Pie' },
    ],
    'bar'
  );

  const xSelect = createSelect(
    'chart-x-select',
    xOptions.map((c) => ({ value: c, label: c })),
    defaultX
  );

  const ySelect = createSelect(
    'chart-y-select',
    classification.numeric.map((c) => ({ value: c, label: c })),
    defaultY
  );

  container.appendChild(createControlGroup('Chart type', typeSelect));
  container.appendChild(createControlGroup('X-axis', xSelect));
  container.appendChild(createControlGroup('Y-axis', ySelect));

  const emit = () => {
    onChange(typeSelect.value as ChartType, xSelect.value, ySelect.value);
  };

  typeSelect.addEventListener('change', emit);
  xSelect.addEventListener('change', emit);
  ySelect.addEventListener('change', emit);

  // Render initial chart from defaults.
  emit();

  return true;
}

function createSelect(
  className: string,
  options: { value: string; label: string }[],
  selected: string
): HTMLSelectElement {
  const select = document.createElement('select');
  select.className = className;
  options.forEach((opt) => {
    const option = document.createElement('option');
    option.value = opt.value;
    option.textContent = opt.label;
    if (opt.value === selected) option.selected = true;
    select.appendChild(option);
  });
  return select;
}

function createControlGroup(labelText: string, control: HTMLElement): HTMLElement {
  const group = document.createElement('div');
  group.className = 'chart-control-group';

  const label = document.createElement('label');
  label.textContent = labelText;
  label.appendChild(control);

  group.appendChild(label);
  return group;
}
