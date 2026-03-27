import './style.css'
import { api } from './api/client'
import { Chart, registerables } from 'chart.js'

Chart.register(...registerables)

// Global state
let currentChart: Chart | null = null;

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
  
  // Reset chart panel on new query
  const chartPanel = document.getElementById('chart-panel') as HTMLElement;
  chartPanel.style.display = 'none';
  if (currentChart) {
    currentChart.destroy();
    currentChart = null;
  }

  // Initialize toggle button
  const toggleButton = document.getElementById('toggle-results') as HTMLButtonElement;
  toggleButton.addEventListener('click', () => {
    resultsContainer.style.display = resultsContainer.style.display === 'none' ? 'block' : 'none';
    toggleButton.textContent = resultsContainer.style.display === 'none' ? 'Show' : 'Hide';
  });

  // Remove existing button container unconditionally
  const resultsHeader = document.querySelector('.results-header') as HTMLElement;
  const existingButtonContainer = resultsHeader?.querySelector('.results-header-buttons');
  if (existingButtonContainer) {
    existingButtonContainer.remove();
  }

  // Add export button if results exist
  if (!response.error && response.results.length > 0) {
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
    
    // Create visualize button
    const visualizeButton = document.createElement('button');
    visualizeButton.className = 'visualize-button secondary-button';
    visualizeButton.innerHTML = '<svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><rect x="1" y="8" width="3" height="7"/><rect x="5.5" y="4" width="3" height="11"/><rect x="10" y="1" width="3" height="14"/></svg> Visualize';
    let chartInitialized = false;
    visualizeButton.onclick = () => {
      if (chartPanel.style.display === 'none') {
        chartPanel.style.display = 'block';
        if (!chartInitialized) {
          initializeChartPanel(response);
          chartInitialized = true;
        }
      } else {
        chartPanel.style.display = 'none';
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

// Chart visualization helpers
const CHART_COLORS = [
  '#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe',
  '#00f2fe', '#43e97b', '#fa709a', '#fee140', '#a18cd1',
  '#fbc2eb', '#8fd3f4', '#a6c0fe', '#d4fc79', '#96e6a1'
];

function classifyColumns(results: Record<string, any>[], columns: string[]): { numericColumns: string[], categoricalColumns: string[] } {
  const numericColumns: string[] = [];
  const categoricalColumns: string[] = [];
  const idPattern = /^(id|rowid)$|_id$/i;

  for (const col of columns) {
    let numericCount = 0;
    let totalNonNull = 0;

    for (const row of results) {
      const val = row[col];
      if (val === null || val === undefined || val === '') continue;
      totalNonNull++;
      if (!isNaN(parseFloat(String(val)))) numericCount++;
    }

    const isNumeric = totalNonNull > 0 && numericCount / totalNonNull > 0.5;
    if (isNumeric && !idPattern.test(col)) {
      numericColumns.push(col);
    } else {
      categoricalColumns.push(col);
    }
  }

  return { numericColumns, categoricalColumns };
}

function getDefaultAxes(numericColumns: string[], categoricalColumns: string[]): { xColumn: string | null, yColumn: string | null } {
  const xColumn = categoricalColumns.length > 0 ? categoricalColumns[0] : (numericColumns.length > 0 ? numericColumns[0] : null);
  const yColumn = numericColumns.length > 0 ? numericColumns[0] : null;
  return { xColumn, yColumn };
}

function renderChart(results: Record<string, any>[], chartType: string, xColumn: string, yColumn: string) {
  const canvas = document.getElementById('chart-canvas') as HTMLCanvasElement;
  if (currentChart) {
    currentChart.destroy();
    currentChart = null;
  }

  const labels: string[] = [];
  const values: number[] = [];

  for (const row of results) {
    const label = String(row[xColumn] ?? '');
    const val = parseFloat(String(row[yColumn]));
    if (isNaN(val)) continue;
    labels.push(label);
    values.push(val);
  }

  let finalLabels = labels;
  let finalValues = values;
  let backgroundColors: string[] = CHART_COLORS;

  if (chartType === 'pie') {
    // Aggregate by label for pie charts
    const aggregated = new Map<string, number>();
    for (let i = 0; i < labels.length; i++) {
      aggregated.set(labels[i], (aggregated.get(labels[i]) || 0) + values[i]);
    }
    const sorted = [...aggregated.entries()].sort((a, b) => b[1] - a[1]);

    if (sorted.length > 15) {
      const top = sorted.slice(0, 15);
      const otherSum = sorted.slice(15).reduce((sum, [, v]) => sum + v, 0);
      finalLabels = top.map(([k]) => k);
      finalValues = top.map(([, v]) => v);
      finalLabels.push('Other');
      finalValues.push(otherSum);
    } else {
      finalLabels = sorted.map(([k]) => k);
      finalValues = sorted.map(([, v]) => v);
    }
    backgroundColors = finalLabels.map((_, i) => CHART_COLORS[i % CHART_COLORS.length]);
  }

  currentChart = new Chart(canvas, {
    type: chartType as any,
    data: {
      labels: finalLabels,
      datasets: [{
        label: yColumn,
        data: finalValues,
        backgroundColor: chartType === 'pie' ? backgroundColors : CHART_COLORS[0],
        borderColor: chartType === 'line' ? CHART_COLORS[0] : undefined,
        borderWidth: chartType === 'pie' ? 1 : undefined,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: true },
        tooltip: {
          callbacks: {
            label: (context: any) => {
              const val = context.parsed.y ?? context.parsed;
              if (chartType === 'pie') {
                const total = finalValues.reduce((a, b) => a + b, 0);
                const pct = ((Number(context.parsed) / total) * 100).toFixed(1);
                return `${context.label}: ${context.parsed} (${pct}%)`;
              }
              return `${yColumn}: ${val}`;
            }
          }
        }
      },
      ...(chartType !== 'pie' ? {
        scales: {
          x: { title: { display: true, text: xColumn } },
          y: { title: { display: true, text: yColumn }, beginAtZero: true }
        }
      } : {})
    }
  });
}

function initializeChartPanel(response: QueryResponse) {
  const { numericColumns, categoricalColumns } = classifyColumns(response.results, response.columns);
  const chartCanvas = document.getElementById('chart-canvas') as HTMLCanvasElement;
  const noNumericMsg = document.getElementById('no-numeric-message') as HTMLElement;
  const xSelect = document.getElementById('x-axis-select') as HTMLSelectElement;
  const ySelect = document.getElementById('y-axis-select') as HTMLSelectElement;
  const typeSelect = document.getElementById('chart-type-select') as HTMLSelectElement;

  if (numericColumns.length === 0) {
    chartCanvas.style.display = 'none';
    noNumericMsg.style.display = 'block';
    return;
  }

  chartCanvas.style.display = 'block';
  noNumericMsg.style.display = 'none';

  const { xColumn, yColumn } = getDefaultAxes(numericColumns, categoricalColumns);

  // Populate X-axis dropdown with categorical columns only
  xSelect.innerHTML = '';
  const allXOptions = [...categoricalColumns];
  for (const col of allXOptions) {
    const opt = document.createElement('option');
    opt.value = col;
    opt.textContent = col;
    if (col === xColumn) opt.selected = true;
    xSelect.appendChild(opt);
  }

  // Populate Y-axis dropdown with only numeric columns
  ySelect.innerHTML = '';
  for (const col of numericColumns) {
    const opt = document.createElement('option');
    opt.value = col;
    opt.textContent = col;
    if (col === yColumn) opt.selected = true;
    ySelect.appendChild(opt);
  }

  const rerender = () => {
    renderChart(response.results, typeSelect.value, xSelect.value, ySelect.value);
  };

  // Remove old listeners by replacing elements
  const newTypeSelect = typeSelect.cloneNode(true) as HTMLSelectElement;
  typeSelect.parentNode!.replaceChild(newTypeSelect, typeSelect);
  newTypeSelect.addEventListener('change', rerender);

  const newXSelect = xSelect.cloneNode(true) as HTMLSelectElement;
  xSelect.parentNode!.replaceChild(newXSelect, xSelect);
  newXSelect.addEventListener('change', rerender);

  const newYSelect = ySelect.cloneNode(true) as HTMLSelectElement;
  ySelect.parentNode!.replaceChild(newYSelect, ySelect);
  newYSelect.addEventListener('change', rerender);

  renderChart(response.results, typeSelect.value, xColumn!, yColumn!);
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
