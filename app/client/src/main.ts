import './style.css'
import { api } from './api/client'

// Global state
let currentPreviewTable = '';
let currentPage = 1;
let totalPages = 1;

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
    tableName.title = 'Click to preview data';
    tableName.onclick = () => openTablePreview(table.name);
    
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

// Initialize preview modal
function initializePreviewModal() {
  const modal = document.getElementById('preview-modal') as HTMLElement;
  const closeButton = document.getElementById('close-preview-modal') as HTMLButtonElement;
  const prevButton = document.getElementById('prev-page-button') as HTMLButtonElement;
  const nextButton = document.getElementById('next-page-button') as HTMLButtonElement;
  const addRowButton = document.getElementById('add-row-button') as HTMLButtonElement;

  closeButton.addEventListener('click', () => {
    modal.style.display = 'none';
  });

  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      modal.style.display = 'none';
    }
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && modal.style.display === 'flex') {
      modal.style.display = 'none';
    }
  });

  prevButton.addEventListener('click', () => {
    if (currentPage > 1) {
      currentPage--;
      renderPreviewPage();
    }
  });

  nextButton.addEventListener('click', () => {
    if (currentPage < totalPages) {
      currentPage++;
      renderPreviewPage();
    }
  });

  addRowButton.addEventListener('click', () => {
    addNewRow();
  });
}

// Open table preview modal
async function openTablePreview(tableName: string) {
  currentPreviewTable = tableName;
  currentPage = 1;

  const modal = document.getElementById('preview-modal') as HTMLElement;
  const title = document.getElementById('preview-modal-title') as HTMLElement;
  title.textContent = `Preview: ${tableName}`;
  modal.style.display = 'flex';

  await renderPreviewPage();
}

// Render current preview page
async function renderPreviewPage() {
  const container = document.getElementById('preview-table-container') as HTMLElement;
  const pageInfo = document.getElementById('page-info') as HTMLElement;
  const prevButton = document.getElementById('prev-page-button') as HTMLButtonElement;
  const nextButton = document.getElementById('next-page-button') as HTMLButtonElement;

  container.innerHTML = '<p>Loading...</p>';

  try {
    const response = await api.getTablePreview(currentPreviewTable, currentPage, 50);

    if (response.error) {
      container.innerHTML = `<div class="error-message">${response.error}</div>`;
      return;
    }

    totalPages = response.total_pages;
    pageInfo.textContent = `Page ${response.page} of ${totalPages}`;
    prevButton.disabled = currentPage <= 1;
    nextButton.disabled = currentPage >= totalPages;

    // Filter out rowid from display columns but keep it in data
    const displayColumns = response.columns.filter(c => c !== 'rowid');

    if (response.rows.length === 0) {
      container.innerHTML = '<p>No data in this table.</p>';
      return;
    }

    const table = document.createElement('table');
    table.className = 'preview-table';

    // Header
    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');
    displayColumns.forEach(col => {
      const th = document.createElement('th');
      th.textContent = col;
      headerRow.appendChild(th);
    });
    const actionTh = document.createElement('th');
    actionTh.textContent = '';
    actionTh.style.width = '40px';
    headerRow.appendChild(actionTh);
    thead.appendChild(headerRow);
    table.appendChild(thead);

    // Body
    const tbody = document.createElement('tbody');
    response.rows.forEach(row => {
      const tr = document.createElement('tr');
      tr.dataset.rowid = String(row['rowid']);

      displayColumns.forEach(col => {
        const td = document.createElement('td');
        td.textContent = row[col] !== null && row[col] !== undefined ? String(row[col]) : '';
        td.dataset.column = col;
        td.addEventListener('click', () => startCellEdit(td, row['rowid'], col));
        tbody.appendChild(document.createTextNode('')); // no-op for structure
        tr.appendChild(td);
      });

      // Delete button
      const deleteTd = document.createElement('td');
      const deleteBtn = document.createElement('button');
      deleteBtn.className = 'delete-row-button';
      deleteBtn.innerHTML = '&times;';
      deleteBtn.title = 'Delete row';
      deleteBtn.onclick = () => deleteRowAction(row['rowid']);
      deleteTd.appendChild(deleteBtn);
      tr.appendChild(deleteTd);

      tbody.appendChild(tr);
    });
    table.appendChild(tbody);

    container.innerHTML = '';
    container.appendChild(table);
  } catch (error) {
    container.innerHTML = `<div class="error-message">Failed to load preview</div>`;
  }
}

// Start inline cell editing
function startCellEdit(td: HTMLTableCellElement, rowid: number, column: string) {
  if (td.querySelector('input')) return; // already editing

  const originalValue = td.textContent || '';
  const input = document.createElement('input');
  input.type = 'text';
  input.className = 'cell-edit-input';
  input.value = originalValue;

  td.textContent = '';
  td.classList.add('editing');
  td.appendChild(input);
  input.focus();
  input.select();

  const cancelEdit = () => {
    td.classList.remove('editing');
    td.textContent = originalValue;
    // Re-attach click handler
    td.addEventListener('click', () => startCellEdit(td, rowid, column), { once: false });
  };

  const saveEdit = async () => {
    const newValue = input.value;
    if (newValue === originalValue) {
      cancelEdit();
      return;
    }

    try {
      const response = await api.updateRow(currentPreviewTable, {
        column,
        value: newValue,
        rowid
      });
      if (response.success) {
        td.classList.remove('editing');
        td.textContent = newValue;
      } else {
        cancelEdit();
      }
    } catch {
      cancelEdit();
    }
  };

  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      saveEdit();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      cancelEdit();
    }
  });

  input.addEventListener('blur', () => {
    cancelEdit();
  });
}

// Add a new row
function addNewRow() {
  const container = document.getElementById('preview-table-container') as HTMLElement;
  const table = container.querySelector('table');
  if (!table) return;

  const tbody = table.querySelector('tbody');
  if (!tbody) return;

  // Get columns from header (skip the last action column)
  const headers = table.querySelectorAll('thead th');
  const columns: string[] = [];
  headers.forEach((th, i) => {
    if (i < headers.length - 1) {
      columns.push(th.textContent || '');
    }
  });

  const newRow = document.createElement('tr');
  newRow.className = 'new-row';

  columns.forEach(col => {
    const td = document.createElement('td');
    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'new-row-input';
    input.placeholder = col;
    input.dataset.column = col;
    td.appendChild(input);
    newRow.appendChild(td);
  });

  // Save button cell
  const saveTd = document.createElement('td');
  const saveBtn = document.createElement('button');
  saveBtn.className = 'primary-button save-new-row-button';
  saveBtn.textContent = 'Save';
  saveBtn.onclick = async () => {
    const values: Record<string, any> = {};
    newRow.querySelectorAll('.new-row-input').forEach((input) => {
      const inp = input as HTMLInputElement;
      if (inp.value) {
        values[inp.dataset.column!] = inp.value;
      }
    });

    try {
      const response = await api.insertRow(currentPreviewTable, { values });
      if (response.success) {
        await renderPreviewPage();
        await loadDatabaseSchema();
      }
    } catch (error) {
      displayError('Failed to insert row');
    }
  };
  saveTd.appendChild(saveBtn);
  newRow.appendChild(saveTd);

  tbody.insertBefore(newRow, tbody.firstChild);

  // Focus the first input
  const firstInput = newRow.querySelector('input') as HTMLInputElement;
  if (firstInput) firstInput.focus();
}

// Delete a row
async function deleteRowAction(rowid: number) {
  if (!confirm('Are you sure you want to delete this row?')) return;

  try {
    const response = await api.deleteRow(currentPreviewTable, rowid);
    if (response.success) {
      await renderPreviewPage();
      await loadDatabaseSchema();
    }
  } catch (error) {
    displayError('Failed to delete row');
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
