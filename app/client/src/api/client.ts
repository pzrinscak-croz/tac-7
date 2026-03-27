// API client configuration

// Base URL configuration - works in both dev and production
const API_BASE_URL = import.meta.env.DEV 
  ? '/api'  // Proxy to backend in development
  : (import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000') + '/api';  // Direct backend in production

// Generic API request function
async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        ...options.headers,
      }
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('API request failed:', error);
    throw error;
  }
}

// API methods
export const api = {
  // Upload file
  async uploadFile(file: File): Promise<FileUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    
    return apiRequest<FileUploadResponse>('/upload', {
      method: 'POST',
      body: formData
    });
  },
  
  // Process query
  async processQuery(request: QueryRequest): Promise<QueryResponse> {
    return apiRequest<QueryResponse>('/query', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(request)
    });
  },
  
  // Get database schema
  async getSchema(): Promise<DatabaseSchemaResponse> {
    return apiRequest<DatabaseSchemaResponse>('/schema');
  },
  
  // Generate insights
  async generateInsights(request: InsightsRequest): Promise<InsightsResponse> {
    return apiRequest<InsightsResponse>('/insights', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(request)
    });
  },
  
  // Health check
  async healthCheck(): Promise<HealthCheckResponse> {
    return apiRequest<HealthCheckResponse>('/health');
  },
  
  // Generate random query
  async generateRandomQuery(): Promise<RandomQueryResponse> {
    return apiRequest<RandomQueryResponse>('/generate-random-query');
  },
  
  // Export table as CSV
  async exportTable(tableName: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/export/table`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ table_name: tableName })
    });
    
    if (!response.ok) {
      throw new Error(`Export failed: ${response.status}`);
    }
    
    // Get the filename from Content-Disposition header
    const contentDisposition = response.headers.get('Content-Disposition');
    const filenameMatch = contentDisposition?.match(/filename="(.+)"/);
    const filename = filenameMatch ? filenameMatch[1] : `${tableName}_export.csv`;
    
    // Download the file
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  },
  
  // Get table preview
  async getTablePreview(tableName: string, page: number = 1, limit: number = 50): Promise<TablePreviewResponse> {
    return apiRequest<TablePreviewResponse>(`/table/${encodeURIComponent(tableName)}/preview?page=${page}&limit=${limit}`);
  },

  // Update a row cell
  async updateRow(tableName: string, request: RowUpdateRequest): Promise<RowUpdateResponse> {
    return apiRequest<RowUpdateResponse>(`/table/${encodeURIComponent(tableName)}/row`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request)
    });
  },

  // Insert a new row
  async insertRow(tableName: string, request: RowInsertRequest): Promise<RowInsertResponse> {
    return apiRequest<RowInsertResponse>(`/table/${encodeURIComponent(tableName)}/row`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request)
    });
  },

  // Delete a row
  async deleteRow(tableName: string, rowid: number): Promise<RowDeleteResponse> {
    return apiRequest<RowDeleteResponse>(`/table/${encodeURIComponent(tableName)}/row/${rowid}`, {
      method: 'DELETE'
    });
  },

  // Export query results as CSV
  async exportQueryResults(data: any[], columns: string[]): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/export/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ data, columns })
    });
    
    if (!response.ok) {
      throw new Error(`Export failed: ${response.status}`);
    }
    
    // Download the file
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'query_results.csv';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  }
};