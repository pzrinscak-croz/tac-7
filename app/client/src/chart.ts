import {
  Chart,
  BarController,
  LineController,
  PieController,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend,
  Title,
  type ChartConfiguration,
} from 'chart.js';

Chart.register(
  BarController,
  LineController,
  PieController,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend,
  Title,
);

type ChartType = 'bar' | 'line' | 'pie';

const PIE_PALETTE = [
  '#667eea',
  '#764ba2',
  '#f093fb',
  '#f5576c',
  '#4facfe',
  '#43e97b',
  '#fa709a',
  '#fee140',
  '#30cfd0',
  '#a8edea',
  '#ff9a9e',
  '#fbc2eb',
  '#84fab0',
  '#8fd3f4',
  '#d4fc79',
];

function isIdLikeColumn(name: string): boolean {
  const lower = name.toLowerCase();
  return lower === 'id' || lower === 'rowid';
}

function isFiniteNumeric(value: unknown): boolean {
  if (value === null || value === undefined) return false;
  if (typeof value === 'string' && value.trim() === '') return false;
  if (typeof value === 'boolean') return false;
  const n = Number(value as any);
  return Number.isFinite(n);
}

export function classifyColumns(
  results: Record<string, any>[],
  columns: string[],
): { numeric: string[]; categorical: string[] } {
  const numeric: string[] = [];
  const categorical: string[] = [];

  for (const col of columns) {
    if (isIdLikeColumn(col)) {
      categorical.push(col);
      continue;
    }
    let hasNumeric = false;
    for (const row of results) {
      const v = row[col];
      if (v === null || v === undefined) continue;
      if (typeof v === 'string' && v.trim() === '') continue;
      if (isFiniteNumeric(v)) {
        hasNumeric = true;
        break;
      }
    }
    if (hasNumeric) {
      numeric.push(col);
    } else {
      categorical.push(col);
    }
  }

  return { numeric, categorical };
}

export function pickDefaults({
  numeric,
  categorical,
}: {
  numeric: string[];
  categorical: string[];
}): { x: string | null; y: string | null } {
  const y = numeric[0] ?? null;
  const x = categorical[0] ?? numeric[0] ?? null;
  return { x, y };
}

export function toNumericSeries(
  results: Record<string, any>[],
  yCol: string,
): { keptIndices: number[]; values: number[] } {
  const keptIndices: number[] = [];
  const values: number[] = [];
  results.forEach((row, idx) => {
    const raw = row[yCol];
    if (raw === null || raw === undefined) return;
    if (typeof raw === 'string' && raw.trim() === '') return;
    const n = Number(raw);
    if (!Number.isFinite(n)) return;
    keptIndices.push(idx);
    values.push(n);
  });
  return { keptIndices, values };
}

export function aggregatePieSlices(
  labels: string[],
  values: number[],
  max = 15,
): { labels: string[]; values: number[] } {
  if (labels.length !== values.length) {
    throw new Error('labels and values must have the same length');
  }
  if (labels.length <= max) {
    return { labels: [...labels], values: [...values] };
  }
  const paired = labels.map((label, i) => ({ label, value: values[i] }));
  paired.sort((a, b) => b.value - a.value);
  const top = paired.slice(0, max - 1);
  const rest = paired.slice(max - 1);
  const otherSum = rest.reduce((acc, p) => acc + p.value, 0);
  return {
    labels: [...top.map((p) => p.label), 'Other'],
    values: [...top.map((p) => p.value), otherSum],
  };
}

type ChartHost = HTMLElement & { _chart?: Chart };

function destroyExistingChart(host: ChartHost): void {
  if (host._chart) {
    host._chart.destroy();
    host._chart = undefined;
  }
}

function buildBarOrLineConfig(
  type: 'bar' | 'line',
  labels: string[],
  values: number[],
  xCol: string,
  yCol: string,
): ChartConfiguration {
  return {
    type,
    data: {
      labels,
      datasets: [
        {
          label: yCol,
          data: values,
          backgroundColor: 'rgba(102, 126, 234, 0.6)',
          borderColor: 'rgba(102, 126, 234, 1)',
          borderWidth: 2,
          ...(type === 'line' ? { fill: false, tension: 0.2, pointRadius: 4 } : {}),
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { title: { display: true, text: xCol } },
        y: { beginAtZero: true, title: { display: true, text: yCol } },
      },
      plugins: {
        legend: { display: true },
        tooltip: { enabled: true },
        title: { display: true, text: `${yCol} by ${xCol}` },
      },
    },
  };
}

function buildPieConfig(
  labels: string[],
  values: number[],
  yCol: string,
): ChartConfiguration {
  const total = values.reduce((a, b) => a + b, 0);
  return {
    type: 'pie',
    data: {
      labels,
      datasets: [
        {
          data: values,
          backgroundColor: labels.map((_, i) => PIE_PALETTE[i % PIE_PALETTE.length]),
          borderColor: '#ffffff',
          borderWidth: 2,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: true, position: 'right' },
        tooltip: {
          enabled: true,
          callbacks: {
            label: (ctx) => {
              const value = Number(ctx.parsed) || 0;
              const pct = total > 0 ? ((value / total) * 100).toFixed(1) : '0.0';
              return `${ctx.label}: ${value} (${pct}%)`;
            },
          },
        },
        title: { display: true, text: yCol },
      },
    },
  };
}

export function renderChartPanel(
  hostElement: HTMLElement,
  response: QueryResponse,
): void {
  const host = hostElement as ChartHost;
  destroyExistingChart(host);
  host.innerHTML = '';

  const { numeric, categorical } = classifyColumns(response.results, response.columns);
  const defaults = pickDefaults({ numeric, categorical });

  const controls = document.createElement('div');
  controls.className = 'chart-controls';

  const typeLabel = document.createElement('label');
  typeLabel.textContent = 'Chart type';
  const typeSelect = document.createElement('select');
  typeSelect.className = 'chart-type-select';
  (['bar', 'line', 'pie'] as ChartType[]).forEach((t) => {
    const opt = document.createElement('option');
    opt.value = t;
    opt.textContent = t.charAt(0).toUpperCase() + t.slice(1);
    typeSelect.appendChild(opt);
  });
  typeLabel.appendChild(typeSelect);

  const xLabel = document.createElement('label');
  xLabel.textContent = 'X axis';
  const xSelect = document.createElement('select');
  xSelect.className = 'chart-x-select';
  const xCandidates = categorical.length > 0 ? categorical : numeric;
  xCandidates.forEach((c) => {
    const opt = document.createElement('option');
    opt.value = c;
    opt.textContent = c;
    xSelect.appendChild(opt);
  });
  if (defaults.x) xSelect.value = defaults.x;
  xLabel.appendChild(xSelect);

  const yLabel = document.createElement('label');
  yLabel.textContent = 'Y axis';
  const ySelect = document.createElement('select');
  ySelect.className = 'chart-y-select';
  numeric.forEach((c) => {
    const opt = document.createElement('option');
    opt.value = c;
    opt.textContent = c;
    ySelect.appendChild(opt);
  });
  if (defaults.y) ySelect.value = defaults.y;
  yLabel.appendChild(ySelect);

  controls.appendChild(typeLabel);
  controls.appendChild(xLabel);
  controls.appendChild(yLabel);
  host.appendChild(controls);

  if (numeric.length === 0) {
    const empty = document.createElement('div');
    empty.className = 'chart-empty';
    empty.textContent = 'No numeric columns available';
    host.appendChild(empty);
    ySelect.disabled = true;
    return;
  }

  const canvasWrap = document.createElement('div');
  canvasWrap.className = 'chart-canvas-wrapper';
  const canvas = document.createElement('canvas');
  canvas.className = 'chart-canvas';
  canvasWrap.appendChild(canvas);
  host.appendChild(canvasWrap);

  const draw = () => {
    destroyExistingChart(host);
    const chartType = typeSelect.value as ChartType;
    const xCol = xSelect.value;
    const yCol = ySelect.value;
    if (!xCol || !yCol) return;

    const { keptIndices, values } = toNumericSeries(response.results, yCol);
    const labels = keptIndices.map((i) =>
      String(response.results[i][xCol] ?? ''),
    );

    let cfg: ChartConfiguration;
    if (chartType === 'pie') {
      const { labels: pieLabels, values: pieValues } = aggregatePieSlices(
        labels,
        values,
      );
      cfg = buildPieConfig(pieLabels, pieValues, yCol);
    } else {
      cfg = buildBarOrLineConfig(chartType, labels, values, xCol, yCol);
    }

    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    host._chart = new Chart(ctx, cfg);
  };

  typeSelect.addEventListener('change', draw);
  xSelect.addEventListener('change', draw);
  ySelect.addEventListener('change', draw);
  draw();
}

export function destroyChartPanel(hostElement: HTMLElement): void {
  destroyExistingChart(hostElement as ChartHost);
}
