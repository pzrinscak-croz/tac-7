import './style.css'
import { api } from './api/client'
import { Chart, registerables } from 'chart.js'

Chart.register(...registerables)

// Global state

// Chart visualization state (module-scoped)
let chartInstance: Chart | null = null;

// Destroy any live Chart.js instance to avoid canvas-reuse errors and stale charts
function destroyChart() {
  if (chartInstance) {
    chartInstance.destroy();
    chartInstance = null;
  }
}

// Remove the chart panel (if any) and destroy its chart, resetting visualization state
function removeChartPanel() {
  destroyChart();
  const existingPanel = document.getElementById('chart-panel');
  if (existingPanel) {
    existingPanel.remove();
  }
}

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
  initializeQueryInput();
  initializeFileUpload();
  initializeModal();
  initializeRandomQueryButton();
  loadDatabaseSchema();
});

// Helper function to get download icon
function getDownloadIcon(): string {
  return '📊 CSV';
}

// Query Input Functionality
function initializeQueryInput() {
  const queryInput = document.getElementById('query-input') as HTMLTextAreaElement;
  const queryButton = document.getElementById('query-button') as HTMLButtonElement;
  
  // Debouncing state
  let isQueryInProgress = false;
  let debounceTimer: number | null = null;
  const DEBOUNCE_DELAY = 400; // 400ms debounce delay
  
  const executeQuery = async () => {
    const query = queryInput.value.trim();
    if (!query || isQueryInProgress) return;
    
    // Clear any pending debounce timer
    if (debounceTimer) {
      clearTimeout(debounceTimer);
      debounceTimer = null;
    }
    
    isQueryInProgress = true;
    // Ensure UI is disabled (might already be disabled from click handler)
    queryButton.disabled = true;
    queryInput.disabled = true;
    queryButton.innerHTML = '<span class="loading"></span>';
    
    try {
      const response = await api.processQuery({
        query,
        llm_provider: 'openai'  // Default to OpenAI
      });
      
      displayResults(response, query);
      
      // Clear the input field on success
      queryInput.value = '';
    } catch (error) {
      displayError(error instanceof Error ? error.message : 'Query failed');
    } finally {
      isQueryInProgress = false;
      queryButton.disabled = false;
      queryInput.disabled = false;
      queryButton.textContent = 'Query';
    }
  };
  
  queryButton.addEventListener('click', () => {
    const query = queryInput.value.trim();
    if (!query || isQueryInProgress) return;
    
    // Debounce rapid clicks
    if (debounceTimer) {
      clearTimeout(debounceTimer);
    }
    
    // Immediately disable UI
    queryButton.disabled = true;
    queryInput.disabled = true;
    queryButton.innerHTML = '<span class="loading"></span>';
    
    debounceTimer = setTimeout(() => {
      executeQuery();
    }, DEBOUNCE_DELAY) as unknown as number;
  });
  
  // Allow Cmd+Enter (Mac) or Ctrl+Enter (Windows/Linux) to submit
  queryInput.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      queryButton.click();
    }
  });
}

// Random Query Generation Functionality
function initializeRandomQueryButton() {
  const generateButton = document.getElementById('generate-random-query-button') as HTMLButtonElement;
  const queryInput = document.getElementById('query-input') as HTMLTextAreaElement;
  
  generateButton.addEventListener('click', async () => {
    generateButton.disabled = true;
    generateButton.innerHTML = '<span class="loading-secondary"></span>';
    
    try {
      const response = await api.generateRandomQuery();
      
      // Always populate the query input field, even with error messages
      queryInput.value = response.query;
      queryInput.focus();
      
      if (response.error && response.error !== "No tables found in database") {
        // Only show errors for unexpected failures
        displayError(response.error);
      }
    } catch (error) {
      displayError(error instanceof Error ? error.message : 'Failed to generate random query');
    } finally {
      generateButton.disabled = false;
      generateButton.textContent = 'Generate Random Query';
    }
  });
}

// File Upload Functionality
function initializeFileUpload() {
  const dropZone = document.getElementById('drop-zone') as HTMLDivElement;
  const fileInput = document.getElementById('file-input') as HTMLInputElement;
  const browseButton = document.getElementById('browse-button') as HTMLButtonElement;
  
  // Browse button click
  browseButton.addEventListener('click', () => fileInput.click());
  
  // File input change
  fileInput.addEventListener('change', (e) => {
    const files = (e.target as HTMLInputElement).files;
    if (files && files.length > 0) {
      handleFileUpload(files[0]);
    }
  });
  
  // Drag and drop
  dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
  });
  
  dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
  });
  
  dropZone.addEventListener('drop', async (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    
    const files = e.dataTransfer?.files;
    if (files && files.length > 0) {
      handleFileUpload(files[0]);
    }
  });
}

// Handle file upload
async function handleFileUpload(file: File) {
  try {
    const response = await api.uploadFile(file);
    
    if (response.error) {
      displayError(response.error);
    } else {
      displayUploadSuccess(response);
      await loadDatabaseSchema();
    }
  } catch (error) {
    displayError(error instanceof Error ? error.message : 'Upload failed');
  }
}

// Load database schema
async function loadDatabaseSchema() {
  try {
    const response = await api.getSchema();
    if (!response.error) {
      displayTables(response.tables);
    }
  } catch (error) {
    console.error('Failed to load schema:', error);
  }
}

// Display query results
function displayResults(response: QueryResponse, query: string) {
  
  const resultsSection = document.getElementById('results-section') as HTMLElement;
  const sqlDisplay = document.getElementById('sql-display') as HTMLDivElement;
  const resultsContainer = document.getElementById('results-container') as HTMLDivElement;
  
  resultsSection.style.display = 'block';

  // Reset any visualization from a previous query so it never lingers
  removeChartPanel();

  // Remove any stale Visualize button; it is re-created only for non-empty results
  // so it stays hidden when a query returns 0 rows (acceptance criterion 9).
  const staleVisualizeButton = document.querySelector('.visualize-button');
  if (staleVisualizeButton) {
    staleVisualizeButton.remove();
  }

  // Display natural language query and SQL
  sqlDisplay.innerHTML = `
    <div class="query-display">
      <strong>Query:</strong> ${query}
    </div>
    <div class="sql-query">
      <strong>SQL:</strong> <code>${response.sql}</code>
    </div>
  `;
  
  // Display results table
  if (response.error) {
    resultsContainer.innerHTML = `<div class="error-message">${response.error}</div>`;
  } else if (response.results.length === 0) {
    resultsContainer.innerHTML = '<p>No results found.</p>';
  } else {
    const table = createResultsTable(response.results, response.columns);
    resultsContainer.innerHTML = '';
    resultsContainer.appendChild(table);
  }
  
  // Initialize toggle button
  const toggleButton = document.getElementById('toggle-results') as HTMLButtonElement;
  toggleButton.addEventListener('click', () => {
    resultsContainer.style.display = resultsContainer.style.display === 'none' ? 'block' : 'none';
    toggleButton.textContent = resultsContainer.style.display === 'none' ? 'Show' : 'Hide';
  });
  
  // Add export button if results exist
  if (!response.error && response.results.length > 0) {
    const resultsHeader = document.querySelector('.results-header') as HTMLElement;
    
    // Remove existing button container if any
    const existingButtonContainer = resultsHeader.querySelector('.results-header-buttons');
    if (existingButtonContainer) {
      existingButtonContainer.remove();
    }
    
    // Create button container
    const buttonContainer = document.createElement('div');
    buttonContainer.className = 'results-header-buttons';
    
    // Create export button
    const exportButton = document.createElement('button');
    exportButton.className = 'export-button secondary-button';
    exportButton.innerHTML = `${getDownloadIcon()} Export`;
    exportButton.title = 'Export results as CSV';
    exportButton.onclick = async () => {
      try {
        await api.exportQueryResults(response.results, response.columns);
      } catch (error) {
        displayError('Failed to export results');
      }
    };

    // Create visualize button (only exists for non-empty results -> hidden for 0 rows)
    const visualizeButton = document.createElement('button');
    visualizeButton.className = 'visualize-button secondary-button';
    visualizeButton.innerHTML = '📈 Visualize';
    visualizeButton.title = 'Visualize results as a chart';
    visualizeButton.onclick = () => {
      const panel = document.getElementById('chart-panel');
      if (panel) {
        // Panel already exists: toggle its visibility
        panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
      } else {
        // First open: build and render the panel
        buildChartPanel(response.results, response.columns);
      }
    };

    // Remove toggle button from its current position
    toggleButton.remove();

    // Add buttons to container
    buttonContainer.appendChild(exportButton);
    buttonContainer.appendChild(visualizeButton);
    buttonContainer.appendChild(toggleButton);

    // Add container to results header
    resultsHeader.appendChild(buttonContainer);
  }
}

// ---- Chart visualization helpers ----

// Parse a value into a finite number, or null. Strips currency symbols and
// thousands separators so numeric columns stored as strings are not misclassified.
function parseNumericValue(value: any): number | null {
  if (value === null || value === undefined) return null;
  if (typeof value === 'number') {
    return Number.isFinite(value) ? value : null;
  }
  if (typeof value === 'boolean') return null;
  const str = String(value).trim();
  if (str === '') return null;
  // Remove common currency symbols, thousands separators, and surrounding whitespace
  const cleaned = str.replace(/[$€£¥,\s]/g, '');
  if (cleaned === '' || cleaned === '-' || cleaned === '.') return null;
  const num = Number(cleaned);
  return Number.isFinite(num) ? num : null;
}

// Classify columns as numeric or categorical by inspecting actual data values.
// A column is numeric when it has at least one non-null value AND every non-null
// value parses to a finite number.
function classifyColumns(results: Record<string, any>[], columns: string[]): ClassifiedColumns {
  const numeric: string[] = [];
  const categorical: string[] = [];

  // Bound the sample size for very large result sets
  const sample = results.length > 500 ? results.slice(0, 500) : results;

  columns.forEach(col => {
    let hasValue = false;
    let allNumeric = true;

    for (const row of sample) {
      const raw = row[col];
      if (raw === null || raw === undefined || String(raw).trim() === '') {
        continue; // treat as missing
      }
      hasValue = true;
      if (parseNumericValue(raw) === null) {
        allNumeric = false;
        break;
      }
    }

    if (hasValue && allNumeric) {
      numeric.push(col);
    } else {
      categorical.push(col);
    }
  });

  return { numeric, categorical };
}

// Default X = first categorical column (fallback: first column overall)
function pickDefaultX(classified: ClassifiedColumns, columns: string[]): string {
  if (classified.categorical.length > 0) return classified.categorical[0];
  return columns[0];
}

// Default Y = first numeric column not named id/rowid (fallback: first numeric)
function pickDefaultY(classified: ClassifiedColumns): string {
  const nonId = classified.numeric.find(
    col => col.toLowerCase() !== 'id' && col.toLowerCase() !== 'rowid'
  );
  return nonId ?? classified.numeric[0];
}

// Build and insert the chart panel below the results container, then render.
function buildChartPanel(results: Record<string, any>[], columns: string[]) {
  const resultsSection = document.getElementById('results-section') as HTMLElement;

  // Remove any stale panel/chart first
  removeChartPanel();

  const panel = document.createElement('div');
  panel.id = 'chart-panel';
  panel.className = 'chart-panel';

  const classified = classifyColumns(results, columns);

  // No numeric columns -> show message, no controls, no chart
  if (classified.numeric.length === 0) {
    const message = document.createElement('p');
    message.className = 'chart-no-data';
    message.textContent = 'No numeric columns available';
    panel.appendChild(message);
    resultsSection.appendChild(panel);
    return;
  }

  const xColumns = classified.categorical.length > 0 ? classified.categorical : columns;
  const defaultX = pickDefaultX(classified, columns);
  const defaultY = pickDefaultY(classified);

  // Controls row
  const controls = document.createElement('div');
  controls.className = 'chart-controls';

  const typeSelect = createLabeledSelect('chart-type-select', 'Chart Type', [
    { value: 'bar', label: 'Bar' },
    { value: 'line', label: 'Line' },
    { value: 'pie', label: 'Pie' },
  ], 'bar');

  const xSelect = createLabeledSelect(
    'chart-x-select',
    'X-Axis',
    xColumns.map(c => ({ value: c, label: c })),
    defaultX
  );

  const ySelect = createLabeledSelect(
    'chart-y-select',
    'Y-Axis',
    classified.numeric.map(c => ({ value: c, label: c })),
    defaultY
  );

  controls.appendChild(typeSelect.wrapper);
  controls.appendChild(xSelect.wrapper);
  controls.appendChild(ySelect.wrapper);

  // Canvas container (fixed height so maintainAspectRatio:false fills it)
  const canvasContainer = document.createElement('div');
  canvasContainer.className = 'chart-canvas-container';
  const canvas = document.createElement('canvas');
  canvas.id = 'results-chart';
  canvasContainer.appendChild(canvas);

  panel.appendChild(controls);
  panel.appendChild(canvasContainer);
  resultsSection.appendChild(panel);

  const rerender = () => {
    renderChart(
      results,
      typeSelect.select.value as ChartKind,
      xSelect.select.value,
      ySelect.select.value
    );
  };

  typeSelect.select.addEventListener('change', rerender);
  xSelect.select.addEventListener('change', rerender);
  ySelect.select.addEventListener('change', rerender);

  // Initial render
  rerender();
}

// Create a labeled <select> control, returning the wrapper and the select element.
function createLabeledSelect(
  id: string,
  labelText: string,
  options: { value: string; label: string }[],
  selected: string
): { wrapper: HTMLDivElement; select: HTMLSelectElement } {
  const wrapper = document.createElement('div');
  wrapper.className = 'chart-control';

  const label = document.createElement('label');
  label.htmlFor = id;
  label.textContent = labelText;

  const select = document.createElement('select');
  select.id = id;
  select.className = 'chart-select';
  options.forEach(opt => {
    const option = document.createElement('option');
    option.value = opt.value;
    option.textContent = opt.label;
    if (opt.value === selected) option.selected = true;
    select.appendChild(option);
  });

  wrapper.appendChild(label);
  wrapper.appendChild(select);
  return { wrapper, select };
}

// Render (or re-render) the chart from the current control selections.
function renderChart(
  results: Record<string, any>[],
  kind: ChartKind,
  xColumn: string,
  yColumn: string
) {
  const canvas = document.getElementById('results-chart') as HTMLCanvasElement | null;
  if (!canvas || !xColumn || !yColumn) return;

  // Always destroy the previous chart before creating a new one
  destroyChart();

  const primary = '#667eea';
  const secondary = '#764ba2';

  if (kind === 'pie') {
    // Aggregate Y values by X label (sum), so duplicate categories combine
    const totals = new Map<string, number>();
    results.forEach(row => {
      const y = parseNumericValue(row[yColumn]);
      if (y === null) return;
      const label = row[xColumn] !== null && row[xColumn] !== undefined ? String(row[xColumn]) : '(empty)';
      totals.set(label, (totals.get(label) ?? 0) + y);
    });

    let entries = Array.from(totals.entries()).sort((a, b) => b[1] - a[1]);

    // Cap at 15 slices, grouping the remainder into "Other"
    const MAX_SLICES = 15;
    if (entries.length > MAX_SLICES) {
      const top = entries.slice(0, MAX_SLICES);
      const otherTotal = entries.slice(MAX_SLICES).reduce((sum, [, v]) => sum + v, 0);
      top.push(['Other', otherTotal]);
      entries = top;
    }

    const labels = entries.map(([label]) => label);
    const data = entries.map(([, value]) => value);
    const colors = labels.map((_, i) => pieColor(i));

    chartInstance = new Chart(canvas, {
      type: 'pie',
      data: {
        labels,
        datasets: [{ data, backgroundColor: colors, borderColor: '#ffffff', borderWidth: 1 }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: true, position: 'right' },
          tooltip: {
            callbacks: {
              label: (ctx) => {
                const value = ctx.parsed as number;
                const total = data.reduce((sum, v) => sum + v, 0);
                const pct = total > 0 ? ((value / total) * 100).toFixed(1) : '0.0';
                return `${ctx.label}: ${value} (${pct}%)`;
              },
            },
          },
        },
      },
    });
    return;
  }

  // Bar / Line: build labels and parsed numeric data, dropping null Y rows
  const labels: string[] = [];
  const data: number[] = [];
  results.forEach(row => {
    const y = parseNumericValue(row[yColumn]);
    if (y === null) return;
    labels.push(row[xColumn] !== null && row[xColumn] !== undefined ? String(row[xColumn]) : '(empty)');
    data.push(y);
  });

  chartInstance = new Chart(canvas, {
    type: kind,
    data: {
      labels,
      datasets: [{
        label: yColumn,
        data,
        backgroundColor: kind === 'line' ? 'rgba(102, 126, 234, 0.2)' : primary,
        borderColor: secondary,
        borderWidth: kind === 'line' ? 2 : 1,
        fill: kind === 'line',
        tension: 0.2,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: true, position: 'top' },
        tooltip: { enabled: true },
      },
      scales: {
        x: {
          title: { display: true, text: xColumn },
        },
        y: {
          beginAtZero: true,
          title: { display: true, text: yColumn },
        },
      },
    },
  });
}

// Distinct-ish colors for pie slices, cycling through the app palette
function pieColor(index: number): string {
  const palette = [
    '#667eea', '#764ba2', '#28a745', '#dc3545', '#f39c12',
    '#17a2b8', '#e83e8c', '#20c997', '#fd7e14', '#6610f2',
    '#6f42c1', '#007bff', '#ffc107', '#e74c3c', '#1abc9c',
    '#95a5a6',
  ];
  return palette[index % palette.length];
}

// Create results table
function createResultsTable(results: Record<string, any>[], columns: string[]): HTMLTableElement {
  const table = document.createElement('table');
  table.className = 'results-table';
  
  // Header
  const thead = document.createElement('thead');
  const headerRow = document.createElement('tr');
  columns.forEach(col => {
    const th = document.createElement('th');
    th.textContent = col;
    headerRow.appendChild(th);
  });
  thead.appendChild(headerRow);
  table.appendChild(thead);
  
  // Body
  const tbody = document.createElement('tbody');
  results.forEach(row => {
    const tr = document.createElement('tr');
    columns.forEach(col => {
      const td = document.createElement('td');
      td.textContent = row[col] !== null ? String(row[col]) : '';
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  
  return table;
}

// Display tables
function displayTables(tables: TableSchema[]) {
  const tablesList = document.getElementById('tables-list') as HTMLDivElement;
  
  if (tables.length === 0) {
    tablesList.innerHTML = '<p class="no-tables">No tables loaded. Upload data or use sample data to get started.</p>';
    return;
  }
  
  tablesList.innerHTML = '';
  
  tables.forEach(table => {
    const tableItem = document.createElement('div');
    tableItem.className = 'table-item';
    
    // Header section
    const tableHeader = document.createElement('div');
    tableHeader.className = 'table-header';
    
    const tableLeft = document.createElement('div');
    tableLeft.style.display = 'flex';
    tableLeft.style.alignItems = 'center';
    tableLeft.style.gap = '1rem';
    
    const tableName = document.createElement('div');
    tableName.className = 'table-name';
    tableName.textContent = table.name;
    
    const tableInfo = document.createElement('div');
    tableInfo.className = 'table-info';
    tableInfo.textContent = `${table.row_count} rows, ${table.columns.length} columns`;
    
    tableLeft.appendChild(tableName);
    tableLeft.appendChild(tableInfo);
    
    // Create buttons container
    const buttonsContainer = document.createElement('div');
    buttonsContainer.style.display = 'flex';
    buttonsContainer.style.gap = '0.5rem';
    buttonsContainer.style.alignItems = 'center';
    
    // Create export button
    const exportButton = document.createElement('button');
    exportButton.className = 'export-button table-export-button';
    exportButton.innerHTML = getDownloadIcon();
    exportButton.title = 'Export table as CSV';
    exportButton.onclick = async () => {
      try {
        await api.exportTable(table.name);
      } catch (error) {
        displayError('Failed to export table');
      }
    };
    
    const removeButton = document.createElement('button');
    removeButton.className = 'remove-table-button';
    removeButton.innerHTML = '&times;';
    removeButton.title = 'Remove table';
    removeButton.onclick = () => removeTable(table.name);
    
    buttonsContainer.appendChild(exportButton);
    buttonsContainer.appendChild(removeButton);
    
    tableHeader.appendChild(tableLeft);
    tableHeader.appendChild(buttonsContainer);
    
    // Columns section
    const tableColumns = document.createElement('div');
    tableColumns.className = 'table-columns';
    
    table.columns.forEach(column => {
      const columnTag = document.createElement('span');
      columnTag.className = 'column-tag';
      
      const columnName = document.createElement('span');
      columnName.className = 'column-name';
      columnName.textContent = column.name;
      
      const columnType = document.createElement('span');
      columnType.className = 'column-type';
      const typeEmoji = getTypeEmoji(column.type);
      columnType.textContent = `${typeEmoji} ${column.type}`;
      
      columnTag.appendChild(columnName);
      columnTag.appendChild(columnType);
      tableColumns.appendChild(columnTag);
    });
    
    tableItem.appendChild(tableHeader);
    tableItem.appendChild(tableColumns);
    tablesList.appendChild(tableItem);
  });
}

// Display upload success
function displayUploadSuccess(response: FileUploadResponse) {
  // Close modal
  const modal = document.getElementById('upload-modal') as HTMLElement;
  modal.style.display = 'none';
  
  // Show success message
  const successDiv = document.createElement('div');
  successDiv.className = 'success-message';
  successDiv.textContent = `Table "${response.table_name}" created successfully with ${response.row_count} rows!`;
  successDiv.style.cssText = `
    background: rgba(40, 167, 69, 0.1);
    border: 1px solid var(--success-color);
    color: var(--success-color);
    padding: 1rem;
    border-radius: 8px;
    margin-bottom: 1rem;
  `;
  
  const tablesSection = document.getElementById('tables-section') as HTMLElement;
  tablesSection.insertBefore(successDiv, tablesSection.firstChild);
  
  // Remove success message after 3 seconds
  setTimeout(() => {
    successDiv.remove();
  }, 3000);
}

// Display error
function displayError(message: string) {
  const errorDiv = document.createElement('div');
  errorDiv.className = 'error-message';
  errorDiv.textContent = message;
  
  const resultsContainer = document.getElementById('results-container') as HTMLDivElement;
  resultsContainer.innerHTML = '';
  resultsContainer.appendChild(errorDiv);
  
  const resultsSection = document.getElementById('results-section') as HTMLElement;
  resultsSection.style.display = 'block';
}

// Initialize modal
function initializeModal() {
  const uploadButton = document.getElementById('upload-data-button') as HTMLButtonElement;
  const modal = document.getElementById('upload-modal') as HTMLElement;
  const closeButton = modal.querySelector('.close-modal') as HTMLButtonElement;
  
  // Open modal
  uploadButton.addEventListener('click', () => {
    modal.style.display = 'flex';
  });
  
  // Close modal
  closeButton.addEventListener('click', () => {
    modal.style.display = 'none';
  });
  
  // Close on background click
  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      modal.style.display = 'none';
    }
  });
  
  // Initialize sample data buttons
  const sampleButtons = modal.querySelectorAll('.sample-button');
  sampleButtons.forEach(button => {
    button.addEventListener('click', async (e) => {
      const sampleType = (e.currentTarget as HTMLElement).dataset.sample;
      await loadSampleData(sampleType!);
    });
  });
}

// Remove table
async function removeTable(tableName: string) {
  if (!confirm(`Are you sure you want to remove the table "${tableName}"?`)) {
    return;
  }
  
  try {
    const response = await fetch(`/api/table/${tableName}`, {
      method: 'DELETE'
    });
    
    if (!response.ok) {
      throw new Error('Failed to remove table');
    }
    
    // Reload schema
    await loadDatabaseSchema();
    
    // Show success message
    const successDiv = document.createElement('div');
    successDiv.className = 'success-message';
    successDiv.textContent = `Table "${tableName}" removed successfully!`;
    successDiv.style.cssText = `
      background: rgba(40, 167, 69, 0.1);
      border: 1px solid var(--success-color);
      color: var(--success-color);
      padding: 1rem;
      border-radius: 8px;
      margin-bottom: 1rem;
    `;
    
    const tablesSection = document.getElementById('tables-section') as HTMLElement;
    tablesSection.insertBefore(successDiv, tablesSection.firstChild);
    
    setTimeout(() => {
      successDiv.remove();
    }, 3000);
  } catch (error) {
    displayError(error instanceof Error ? error.message : 'Failed to remove table');
  }
}

// Get emoji for data type
function getTypeEmoji(type: string): string {
  const upperType = type.toUpperCase();
  
  // SQLite types
  if (upperType.includes('INT')) return '🔢';
  if (upperType.includes('REAL') || upperType.includes('FLOAT') || upperType.includes('DOUBLE')) return '💯';
  if (upperType.includes('TEXT') || upperType.includes('CHAR') || upperType.includes('STRING')) return '📝';
  if (upperType.includes('DATE') || upperType.includes('TIME')) return '📅';
  if (upperType.includes('BOOL')) return '✓';
  if (upperType.includes('BLOB')) return '📦';
  
  // Default
  return '📊';
}

// Load sample data
async function loadSampleData(sampleType: string) {
  try {
    let filename: string;
    
    if (sampleType === 'users') {
      filename = 'users.json';
    } else if (sampleType === 'products') {
      filename = 'products.csv';
    } else if (sampleType === 'events') {
      filename = 'events.jsonl';
    } else {
      throw new Error(`Unknown sample type: ${sampleType}`);
    }
    
    const response = await fetch(`/sample-data/${filename}`);
    
    if (!response.ok) {
      throw new Error('Failed to load sample data');
    }
    
    const blob = await response.blob();
    const file = new File([blob], filename, { type: blob.type });
    
    // Upload the file
    await handleFileUpload(file);
  } catch (error) {
    displayError(error instanceof Error ? error.message : 'Failed to load sample data');
  }
}
