import './style.css'
import { api } from './api/client'
import {
  Chart,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  BarController,
  LineController,
  PieController
} from 'chart.js'

// Register Chart.js components
Chart.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  BarController,
  LineController,
  PieController
)

// Global state
let currentResults: Record<string, any>[] = [];
let currentColumns: string[] = [];
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

  // Store results globally for chart visualization
  currentResults = response.results || [];
  currentColumns = response.columns || [];

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

  // Add export and visualize buttons if results exist with rows
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

    // Create visualize button
    const visualizeButton = document.createElement('button');
    visualizeButton.className = 'export-button visualize-button';
    visualizeButton.innerHTML = '📈 Visualize';
    visualizeButton.title = 'Create chart visualization';
    visualizeButton.onclick = () => showVisualizeModal();

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

    // Remove toggle button from its current position
    toggleButton.remove();

    // Add buttons to container
    buttonContainer.appendChild(visualizeButton);
    buttonContainer.appendChild(exportButton);
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

// ==================== Chart Visualization Functions ====================

// Classify column as numeric or categorical based on sample values
function isNumericColumn(results: Record<string, any>[], column: string): boolean {
  if (results.length === 0) return false;

  // Check first 10 rows to determine column type
  const sampleSize = Math.min(10, results.length);
  let numericCount = 0;
  let totalCount = 0;

  for (let i = 0; i < sampleSize; i++) {
    const value = results[i][column];
    if (value !== null && value !== undefined && value !== '') {
      totalCount++;
      const parsed = parseNumericValue(value);
      if (parsed !== null) {
        numericCount++;
      }
    }
  }

  // Column is numeric if more than 50% of values parse as numbers
  return totalCount > 0 && numericCount / totalCount >= 0.5;
}

// Get default X and Y column selections
function getDefaultChartColumns(results: Record<string, any>[], columns: string[]): { xColumn: string | null, yColumn: string | null } {
  let textColumn: string | null = null;
  let numericColumn: string | null = null;

  // Exclude id/rowid from numeric column selection
  const excludedColumns = ['id', 'rowid', 'ID', 'ROWID', 'Id', 'Rowid'];

  for (const col of columns) {
    // Find first text column for X-axis
    if (!textColumn && !isNumericColumn(results, col)) {
      textColumn = col;
    }

    // Find first numeric column for Y-axis (excluding id columns)
    if (!numericColumn && isNumericColumn(results, col) && !excludedColumns.includes(col)) {
      numericColumn = col;
    }

    // Stop if we found both
    if (textColumn && numericColumn) break;
  }

  return { xColumn: textColumn, yColumn: numericColumn };
}

// Parse value as number, returning null if not parseable
function parseNumericValue(value: any): number | null {
  if (value === null || value === undefined || value === '') return null;

  const num = Number(value);
  if (isNaN(num) || !isFinite(num)) return null;

  return num;
}

// Prepare chart data for Chart.js
function prepareChartData(
  results: Record<string, any>[],
  xColumn: string,
  yColumn: string
): { labels: string[], data: number[], colors: string[] } {
  const labels: string[] = [];
  const data: number[] = [];
  const colors: string[] = [];

  // Color palette for charts
  const colorPalette = [
    'rgba(102, 126, 234, 0.8)',
    'rgba(118, 75, 162, 0.8)',
    'rgba(40, 167, 69, 0.8)',
    'rgba(255, 193, 7, 0.8)',
    'rgba(220, 53, 69, 0.8)',
    'rgba(23, 162, 184, 0.8)',
    'rgba(253, 126, 20, 0.8)',
    'rgba(111, 66, 193, 0.8)',
    'rgba(0, 123, 255, 0.8)',
    'rgba(40, 199, 111, 0.8)',
    'rgba(232, 62, 140, 0.8)',
    'rgba(108, 117, 125, 0.8)',
    'rgba(255, 159, 67, 0.8)',
    'rgba(0, 214, 143, 0.8)',
    'rgba(165, 14, 255, 0.8)'
  ];

  for (const row of results) {
    labels.push(String(row[xColumn] ?? ''));
    const parsedValue = parseNumericValue(row[yColumn]);
    data.push(parsedValue ?? 0);
    const colorIndex = (labels.length - 1) % colorPalette.length;
    colors.push(colorPalette[colorIndex]);
  }

  return { labels, data, colors };
}

// Show chart configuration modal
function showVisualizeModal() {
  // Store results globally for the modal
  if (currentResults.length === 0 || currentColumns.length === 0) {
    displayError('No results available for visualization');
    return;
  }

  // Check for numeric columns
  const numericColumns = currentColumns.filter(col => isNumericColumn(currentResults, col));
  if (numericColumns.length === 0) {
    displayError('No numeric columns available for visualization');
    return;
  }

  // Get default column selections
  const { xColumn, yColumn } = getDefaultChartColumns(currentResults, currentColumns);

  // Create modal if it doesn't exist
  let modal = document.getElementById('chart-modal') as HTMLElement;
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'chart-modal';
    modal.className = 'modal';
    document.body.appendChild(modal);
  }

  // Build column options
  const textColumns = currentColumns.filter(col => !isNumericColumn(currentResults, col));
  const xColumnOptions = textColumns.length > 0 ? textColumns : currentColumns;
  const yColumnOptions = numericColumns;

  const xOptions = xColumnOptions.map(col => `<option value="${col}" ${col === xColumn ? 'selected' : ''}>${col}</option>`).join('');
  const yOptions = yColumnOptions.map(col => `<option value="${col}" ${col === yColumn ? 'selected' : ''}>${col}</option>`).join('');

  modal.innerHTML = `
    <div class="modal-content chart-modal-content">
      <div class="modal-header">
        <h2>Chart Visualization</h2>
        <button class="close-modal" onclick="closeChartModal()">&times;</button>
      </div>
      <div class="modal-body">
        <div class="chart-config">
          <div class="chart-config-row">
            <label for="chart-type">Chart Type:</label>
            <select id="chart-type" class="chart-select">
              <option value="bar">Bar Chart</option>
              <option value="line">Line Chart</option>
              <option value="pie">Pie Chart</option>
            </select>
          </div>
          <div class="chart-config-row">
            <label for="x-column">X-Axis (Categories):</label>
            <select id="x-column" class="chart-select">
              ${xOptions}
            </select>
          </div>
          <div class="chart-config-row">
            <label for="y-column">Y-Axis (Values):</label>
            <select id="y-column" class="chart-select">
              ${yOptions}
            </select>
          </div>
          <div class="chart-actions">
            <button class="primary-button" onclick="generateChart()">Generate Chart</button>
          </div>
        </div>
        <div id="chart-container" class="chart-container"></div>
      </div>
    </div>
  `;

  modal.style.display = 'flex';

  // Close modal on background click
  modal.onclick = (e) => {
    if (e.target === modal) {
      closeChartModal();
    }
  };

  // Generate initial chart with defaults
  if (xColumn && yColumn) {
    setTimeout(() => generateChart(), 100);
  }
}

// Close chart modal
function closeChartModal() {
  const modal = document.getElementById('chart-modal') as HTMLElement;
  if (modal) {
    modal.style.display = 'none';
  }

  // Destroy chart instance
  if (currentChart) {
    currentChart.destroy();
    currentChart = null;
  }
}

// Generate chart based on current selections
function generateChart() {
  const chartType = (document.getElementById('chart-type') as HTMLSelectElement).value;
  const xColumn = (document.getElementById('x-column') as HTMLSelectElement).value;
  const yColumn = (document.getElementById('y-column') as HTMLSelectElement).value;
  const container = document.getElementById('chart-container') as HTMLDivElement;

  if (!container || !xColumn || !yColumn) return;

  // Destroy existing chart
  if (currentChart) {
    currentChart.destroy();
    currentChart = null;
  }

  // Prepare data
  const { labels, data } = prepareChartData(currentResults, xColumn, yColumn);

  // Handle pie chart slice limiting
  let finalLabels = labels;
  let finalData = data;

  if (chartType === 'pie' && labels.length > 15) {
    const topIndices = data
      .map((val, idx) => ({ val, idx }))
      .sort((a, b) => b.val - a.val)
      .slice(0, 14);

    const otherSum = data
      .filter((_, idx) => !topIndices.some(t => t.idx === idx))
      .reduce((sum, val) => sum + val, 0);

    finalLabels = [...topIndices.map(t => labels[t.idx]), 'Other'];
    finalData = [...topIndices.map(t => data[t.idx]), otherSum];
  }

  // Color palette
  const colors = [
    'rgba(102, 126, 234, 0.8)',
    'rgba(118, 75, 162, 0.8)',
    'rgba(40, 167, 69, 0.8)',
    'rgba(255, 193, 7, 0.8)',
    'rgba(220, 53, 69, 0.8)',
    'rgba(23, 162, 184, 0.8)',
    'rgba(253, 126, 20, 0.8)',
    'rgba(111, 66, 193, 0.8)',
    'rgba(0, 123, 255, 0.8)',
    'rgba(40, 199, 111, 0.8)',
    'rgba(232, 62, 140, 0.8)',
    'rgba(108, 117, 125, 0.8)',
    'rgba(255, 159, 67, 0.8)',
    'rgba(0, 214, 143, 0.8)',
    'rgba(165, 14, 255, 0.8)'
  ];

  // Set container height
  container.style.minHeight = '300px';
  container.innerHTML = '<canvas id="chart-canvas"></canvas>';

  const canvas = document.getElementById('chart-canvas') as HTMLCanvasElement;
  const ctx = canvas.getContext('2d')!;

  // Chart.js configuration
  const chartConfig: any = {
    type: chartType,
    data: {
      labels: finalLabels,
      datasets: [{
        label: yColumn,
        data: finalData,
        backgroundColor: chartType === 'pie'
          ? colors.slice(0, finalData.length)
          : colors[0],
        borderColor: chartType === 'pie'
          ? colors.slice(0, finalData.length)
          : colors[0].replace('0.8', '1'),
        borderWidth: chartType === 'pie' ? 2 : 1,
        tension: 0.3,
        fill: chartType === 'line'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: true,
          position: chartType === 'pie' ? 'right' : 'top',
          labels: {
            boxWidth: 12,
            padding: 10
          }
        },
        tooltip: {
          callbacks: {
            label: chartType === 'pie'
              ? (context: any) => {
                  const total = (context.dataset.data as number[]).reduce((a: number, b: number) => a + b, 0);
                  const value = context.raw;
                  const percentage = ((value / total) * 100).toFixed(1);
                  return `${context.label}: ${value} (${percentage}%)`;
                }
              : (context: any) => `${yColumn}: ${context.raw}`
          }
        }
      },
      scales: chartType === 'pie' ? {} : {
        y: {
          beginAtZero: true,
          title: {
            display: true,
            text: yColumn
          }
        },
        x: {
          title: {
            display: true,
            text: xColumn
          }
        }
      }
    }
  };

  currentChart = new Chart(ctx, chartConfig);
}

// Make functions available globally for onclick handlers
(window as any).showVisualizeModal = showVisualizeModal;
(window as any).closeChartModal = closeChartModal;
(window as any).generateChart = generateChart;
