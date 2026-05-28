import './style.css'
import { api } from './api/client'

// Global state
interface PreviewState {
  tableName: string;
  page: number;
  limit: number;
  totalPages: number;
  totalRows: number;
  columns: string[];
  rows: TablePreviewRow[];
}

let currentPreview: PreviewState | null = null;

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
  initializeQueryInput();
  initializeFileUpload();
  initializeModal();
  initializePreviewModal();
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
    
    // Remove toggle button from its current position
    toggleButton.remove();
    
    // Add buttons to container
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
    tableName.className = 'table-name table-name-clickable';
    tableName.textContent = table.name;
    tableName.title = 'Click to preview and edit this table';
    tableName.onclick = () => openPreview(table.name);
    
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

// Preview Modal
function initializePreviewModal() {
  const modal = document.getElementById('preview-modal') as HTMLElement;
  const closeButton = modal.querySelector('.close-preview-modal') as HTMLButtonElement;
  const prevButton = document.getElementById('preview-prev') as HTMLButtonElement;
  const nextButton = document.getElementById('preview-next') as HTMLButtonElement;
  const addRowButton = document.getElementById('add-row-button') as HTMLButtonElement;

  const closePreview = () => {
    modal.style.display = 'none';
    currentPreview = null;
  };

  closeButton.addEventListener('click', closePreview);
  modal.addEventListener('click', (e) => {
    if (e.target === modal) closePreview();
  });

  prevButton.addEventListener('click', () => {
    if (!currentPreview || currentPreview.page <= 1) return;
    currentPreview.page -= 1;
    loadPreviewPage();
  });

  nextButton.addEventListener('click', () => {
    if (!currentPreview || currentPreview.page >= currentPreview.totalPages) return;
    currentPreview.page += 1;
    loadPreviewPage();
  });

  addRowButton.addEventListener('click', async () => {
    if (!currentPreview) return;
    addRowButton.disabled = true;
    try {
      const response = await api.insertRow(currentPreview.tableName, { values: {} });
      if (!response.success) {
        displayError(response.error || 'Failed to add row');
        return;
      }
      // Jump to last page so user can see the new row
      const newTotal = currentPreview.totalRows + 1;
      const newTotalPages = Math.max(1, Math.ceil(newTotal / currentPreview.limit));
      currentPreview.page = newTotalPages;
      await loadPreviewPage();
      await loadDatabaseSchema();
    } catch (error) {
      displayError(error instanceof Error ? error.message : 'Failed to add row');
    } finally {
      addRowButton.disabled = false;
    }
  });
}

async function openPreview(tableName: string) {
  const modal = document.getElementById('preview-modal') as HTMLElement;
  const title = document.getElementById('preview-modal-title') as HTMLElement;
  title.textContent = `Preview: ${tableName}`;
  currentPreview = {
    tableName,
    page: 1,
    limit: 50,
    totalPages: 1,
    totalRows: 0,
    columns: [],
    rows: []
  };
  modal.style.display = 'flex';
  await loadPreviewPage();
}

async function loadPreviewPage() {
  if (!currentPreview) return;
  try {
    const response = await api.getTablePreview(
      currentPreview.tableName,
      currentPreview.page,
      currentPreview.limit
    );
    if (response.error) {
      displayError(response.error);
      return;
    }

    // Clamp page in case rows were deleted past the current page
    const clampedPage = Math.min(Math.max(1, response.page), response.total_pages);
    if (clampedPage !== currentPreview.page) {
      currentPreview.page = clampedPage;
      const adjusted = await api.getTablePreview(
        currentPreview.tableName,
        clampedPage,
        currentPreview.limit
      );
      currentPreview.columns = adjusted.columns;
      currentPreview.rows = adjusted.rows;
      currentPreview.totalPages = adjusted.total_pages;
      currentPreview.totalRows = adjusted.total_rows;
    } else {
      currentPreview.columns = response.columns;
      currentPreview.rows = response.rows;
      currentPreview.totalPages = response.total_pages;
      currentPreview.totalRows = response.total_rows;
    }

    renderPreviewTable(currentPreview.columns, currentPreview.rows);

    const pageLabel = document.getElementById('preview-page-label') as HTMLElement;
    pageLabel.textContent = `Page ${currentPreview.page} of ${currentPreview.totalPages}`;

    const status = document.getElementById('preview-status') as HTMLElement;
    status.textContent = `${currentPreview.totalRows} rows total`;

    const prevButton = document.getElementById('preview-prev') as HTMLButtonElement;
    const nextButton = document.getElementById('preview-next') as HTMLButtonElement;
    prevButton.disabled = currentPreview.page <= 1;
    nextButton.disabled = currentPreview.page >= currentPreview.totalPages;
  } catch (error) {
    displayError(error instanceof Error ? error.message : 'Failed to load preview');
  }
}

function renderPreviewTable(columns: string[], rows: TablePreviewRow[]) {
  const container = document.getElementById('preview-table-container') as HTMLDivElement;
  container.innerHTML = '';

  const table = document.createElement('table');
  table.className = 'preview-table';

  const thead = document.createElement('thead');
  const headerRow = document.createElement('tr');
  columns.forEach(col => {
    const th = document.createElement('th');
    th.textContent = col;
    headerRow.appendChild(th);
  });
  const deleteHeader = document.createElement('th');
  deleteHeader.textContent = '';
  headerRow.appendChild(deleteHeader);
  thead.appendChild(headerRow);
  table.appendChild(thead);

  const tbody = document.createElement('tbody');
  if (rows.length === 0) {
    const tr = document.createElement('tr');
    const td = document.createElement('td');
    td.colSpan = columns.length + 1;
    td.textContent = 'No rows. Click "+ Add Row" to insert one.';
    td.style.textAlign = 'center';
    td.style.padding = '2rem';
    td.style.color = 'var(--text-secondary)';
    tr.appendChild(td);
    tbody.appendChild(tr);
  } else {
    rows.forEach(row => {
      const tr = document.createElement('tr');
      tr.dataset.rowid = String(row.rowid);

      columns.forEach(col => {
        const td = document.createElement('td');
        td.className = 'editable';
        td.dataset.column = col;
        const val = row.values[col];
        td.textContent = val === null || val === undefined ? '' : String(val);
        td.addEventListener('click', () => beginCellEdit(td, row.rowid, col));
        tr.appendChild(td);
      });

      const deleteTd = document.createElement('td');
      deleteTd.className = 'delete-cell';
      const deleteButton = document.createElement('button');
      deleteButton.className = 'delete-row-button';
      deleteButton.textContent = 'Delete';
      deleteButton.onclick = () => handleDeleteRow(row.rowid);
      deleteTd.appendChild(deleteButton);
      tr.appendChild(deleteTd);

      tbody.appendChild(tr);
    });
  }
  table.appendChild(tbody);
  container.appendChild(table);
}

function beginCellEdit(td: HTMLTableCellElement, rowid: number, column: string) {
  if (td.classList.contains('editing')) return;
  if (!currentPreview) return;

  const originalText = td.textContent || '';
  td.classList.add('editing');
  td.textContent = '';

  const input = document.createElement('input');
  input.type = 'text';
  input.value = originalText;
  td.appendChild(input);
  input.focus();
  input.select();

  let finished = false;

  const revert = () => {
    if (finished) return;
    finished = true;
    td.classList.remove('editing');
    td.textContent = originalText;
  };

  const commit = async () => {
    if (finished) return;
    finished = true;
    const newValue = input.value;
    if (newValue === originalText) {
      td.classList.remove('editing');
      td.textContent = originalText;
      return;
    }
    try {
      const response = await api.updateRowCell(currentPreview!.tableName, {
        rowid,
        column,
        value: newValue
      });
      td.classList.remove('editing');
      if (response.success) {
        td.textContent = newValue;
        const target = currentPreview!.rows.find(r => r.rowid === rowid);
        if (target) target.values[column] = newValue;
      } else {
        td.textContent = originalText;
        displayError(response.error || 'Failed to update cell');
      }
    } catch (error) {
      td.classList.remove('editing');
      td.textContent = originalText;
      displayError(error instanceof Error ? error.message : 'Failed to update cell');
    }
  };

  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      commit();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      revert();
    }
  });
  input.addEventListener('blur', revert);
}

async function handleDeleteRow(rowid: number) {
  if (!currentPreview) return;
  if (!confirm('Delete this row?')) return;
  try {
    const response = await api.deleteRow(currentPreview.tableName, rowid);
    if (!response.success) {
      displayError(response.error || 'Failed to delete row');
      return;
    }
    await loadPreviewPage();
    await loadDatabaseSchema();
  } catch (error) {
    displayError(error instanceof Error ? error.message : 'Failed to delete row');
  }
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
