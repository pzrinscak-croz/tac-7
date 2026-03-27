from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from datetime import datetime
import os
import sqlite3
import traceback
from dotenv import load_dotenv
import logging
import sys

from core.data_models import (
    FileUploadResponse,
    QueryRequest,
    QueryResponse,
    DatabaseSchemaResponse,
    InsightsRequest,
    InsightsResponse,
    HealthCheckResponse,
    TableSchema,
    ColumnInfo,
    RandomQueryResponse,
    ExportRequest,
    QueryExportRequest,
    TablePreviewResponse,
    RowUpdateRequest,
    RowUpdateResponse,
    RowInsertRequest,
    RowInsertResponse,
    RowDeleteResponse,
)
from core.file_processor import convert_csv_to_sqlite, convert_json_to_sqlite, convert_jsonl_to_sqlite
from core.llm_processor import generate_sql, generate_random_query
from core.sql_processor import execute_sql_safely, get_database_schema
from core.insights import generate_insights
from core.sql_security import (
    execute_query_safely,
    validate_identifier,
    check_table_exists,
    SQLSecurityError
)
from core.export_utils import generate_csv_from_data, generate_csv_from_table

# Load .env file from server directory
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Create logger for this module
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Natural Language SQL Interface",
    description="Convert natural language to SQL queries",
    version="1.0.0"
)

# CORS configuration for frontend
frontend_port = os.environ.get("FRONTEND_PORT", "5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[f"http://localhost:{frontend_port}"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global app state
app_start_time = datetime.now()

# Ensure database directory exists
os.makedirs("db", exist_ok=True)

@app.post("/api/upload", response_model=FileUploadResponse)
async def upload_file(file: UploadFile = File(...)) -> FileUploadResponse:
    """Upload and convert .json, .jsonl or .csv file to SQLite table"""
    try:
        # Validate file type
        if not file.filename.endswith(('.csv', '.json', '.jsonl')):
            raise HTTPException(400, "Only .csv, .json, and .jsonl files are supported")
        
        # Generate table name from filename
        table_name = file.filename.rsplit('.', 1)[0].lower().replace(' ', '_')
        
        # Read file content
        content = await file.read()
        
        # Convert to SQLite based on file type
        if file.filename.endswith('.csv'):
            result = convert_csv_to_sqlite(content, table_name)
        elif file.filename.endswith('.jsonl'):
            result = convert_jsonl_to_sqlite(content, table_name)
        else:
            result = convert_json_to_sqlite(content, table_name)
        
        response = FileUploadResponse(
            table_name=result['table_name'],
            table_schema=result['schema'],
            row_count=result['row_count'],
            sample_data=result['sample_data']
        )
        logger.info(f"[SUCCESS] File upload: {response}")
        return response
    except Exception as e:
        logger.error(f"[ERROR] File upload failed: {str(e)}")
        logger.error(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
        return FileUploadResponse(
            table_name="",
            table_schema={},
            row_count=0,
            sample_data=[],
            error=str(e)
        )

@app.post("/api/query", response_model=QueryResponse)
async def process_natural_language_query(request: QueryRequest) -> QueryResponse:
    """Process natural language query and return SQL results"""
    try:
        # Get database schema
        schema_info = get_database_schema()
        
        # Generate SQL using routing logic
        sql = generate_sql(request, schema_info)
        
        # Execute SQL query
        start_time = datetime.now()
        result = execute_sql_safely(sql)
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        
        if result['error']:
            raise Exception(result['error'])
        
        response = QueryResponse(
            sql=sql,
            results=result['results'],
            columns=result['columns'],
            row_count=len(result['results']),
            execution_time_ms=execution_time
        )
        logger.info(f"[SUCCESS] Query processed: SQL={sql}, rows={len(result['results'])}, time={execution_time}ms")
        return response
    except Exception as e:
        logger.error(f"[ERROR] Query processing failed: {str(e)}")
        logger.error(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
        return QueryResponse(
            sql="",
            results=[],
            columns=[],
            row_count=0,
            execution_time_ms=0,
            error=str(e)
        )

@app.get("/api/schema", response_model=DatabaseSchemaResponse)
async def get_database_schema_endpoint() -> DatabaseSchemaResponse:
    """Get current database schema and table information"""
    try:
        schema = get_database_schema()
        tables = []
        
        for table_name, table_info in schema['tables'].items():
            columns = []
            for col_name, col_type in table_info['columns'].items():
                columns.append(ColumnInfo(
                    name=col_name,
                    type=col_type,
                    nullable=True,
                    primary_key=False
                ))
            
            tables.append(TableSchema(
                name=table_name,
                columns=columns,
                row_count=table_info.get('row_count', 0),
                created_at=datetime.now()  # Simplified for v1
            ))
        
        response = DatabaseSchemaResponse(
            tables=tables,
            total_tables=len(tables)
        )
        logger.info(f"[SUCCESS] Schema retrieved: {len(tables)} tables")
        return response
    except Exception as e:
        logger.error(f"[ERROR] Schema retrieval failed: {str(e)}")
        logger.error(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
        return DatabaseSchemaResponse(
            tables=[],
            total_tables=0,
            error=str(e)
        )

@app.post("/api/insights", response_model=InsightsResponse)
async def generate_insights_endpoint(request: InsightsRequest) -> InsightsResponse:
    """Generate statistical insights for table columns"""
    try:
        insights = generate_insights(request.table_name, request.column_names)
        response = InsightsResponse(
            table_name=request.table_name,
            insights=insights,
            generated_at=datetime.now()
        )
        logger.info(f"[SUCCESS] Insights generated for table: {request.table_name}, insights count: {len(insights)}")
        return response
    except Exception as e:
        logger.error(f"[ERROR] Insights generation failed: {str(e)}")
        logger.error(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
        return InsightsResponse(
            table_name=request.table_name,
            insights=[],
            generated_at=datetime.now(),
            error=str(e)
        )

@app.get("/api/generate-random-query", response_model=RandomQueryResponse)
async def generate_random_query_endpoint() -> RandomQueryResponse:
    """Generate a random natural language query based on database schema"""
    try:
        # Get database schema
        schema_info = get_database_schema()
        
        # Check if there are any tables
        if not schema_info.get('tables'):
            return RandomQueryResponse(
                query="Please upload some data first to generate queries.",
                error="No tables found in database"
            )
        
        # Generate random query using LLM
        random_query = generate_random_query(schema_info)
        
        response = RandomQueryResponse(query=random_query)
        logger.info(f"[SUCCESS] Random query generated: {random_query}")
        return response
    except Exception as e:
        logger.error(f"[ERROR] Random query generation failed: {str(e)}")
        logger.error(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
        return RandomQueryResponse(
            query="Could not generate a random query. Please try again.",
            error=str(e)
        )

@app.get("/api/health", response_model=HealthCheckResponse)
async def health_check() -> HealthCheckResponse:
    """Health check endpoint with database status"""
    try:
        # Check database connection
        conn = sqlite3.connect("db/database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        conn.close()
        
        uptime = (datetime.now() - app_start_time).total_seconds()
        
        response = HealthCheckResponse(
            status="ok",
            database_connected=True,
            tables_count=len(tables),
            uptime_seconds=uptime
        )
        logger.info(f"[SUCCESS] Health check: OK, {len(tables)} tables, uptime: {uptime}s")
        return response
    except Exception as e:
        logger.error(f"[ERROR] Health check failed: {str(e)}")
        logger.error(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
        return HealthCheckResponse(
            status="error",
            database_connected=False,
            tables_count=0,
            uptime_seconds=0
        )

@app.delete("/api/table/{table_name}")
async def delete_table(table_name: str):
    """Delete a table from the database"""
    try:
        # Validate table name using security module
        try:
            validate_identifier(table_name, "table")
        except SQLSecurityError as e:
            raise HTTPException(400, str(e))
        
        conn = sqlite3.connect("db/database.db")
        
        # Check if table exists using secure method
        if not check_table_exists(conn, table_name):
            conn.close()
            raise HTTPException(404, f"Table '{table_name}' not found")
        
        # Drop the table using safe query execution with DDL permission
        execute_query_safely(
            conn,
            "DROP TABLE IF EXISTS {table}",
            identifier_params={'table': table_name},
            allow_ddl=True
        )
        conn.commit()
        conn.close()
        
        response = {"message": f"Table '{table_name}' deleted successfully"}
        logger.info(f"[SUCCESS] Table deleted: {table_name}")
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Table deletion failed: {str(e)}")
        logger.error(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
        raise HTTPException(500, f"Error deleting table: {str(e)}")

@app.post("/api/export/table")
async def export_table(request: ExportRequest) -> Response:
    """Export a table as CSV file"""
    try:
        # Validate table name
        validate_identifier(request.table_name, "table")
        
        # Connect to database
        conn = sqlite3.connect("db/database.db")
        
        # Check if table exists
        if not check_table_exists(conn, request.table_name):
            conn.close()
            raise HTTPException(404, f"Table '{request.table_name}' not found")
        
        # Generate CSV
        csv_data = generate_csv_from_table(conn, request.table_name)
        conn.close()
        
        # Return CSV response
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{request.table_name}_export.csv"'
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Table export failed: {str(e)}")
        logger.error(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
        raise HTTPException(500, f"Error exporting table: {str(e)}")

@app.post("/api/export/query")
async def export_query_results(request: QueryExportRequest) -> Response:
    """Export query results as CSV file"""
    try:
        # Generate CSV from query results
        csv_data = generate_csv_from_data(request.data, request.columns)
        
        # Return CSV response
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={
                "Content-Disposition": 'attachment; filename="query_results.csv"'
            }
        )
    except Exception as e:
        logger.error(f"[ERROR] Query export failed: {str(e)}")
        logger.error(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
        raise HTTPException(500, f"Error exporting query results: {str(e)}")

import math

@app.get("/api/table/{table_name}/preview", response_model=TablePreviewResponse)
async def get_table_preview(table_name: str, page: int = 1, limit: int = 50) -> TablePreviewResponse:
    """Get paginated preview of table data"""
    try:
        try:
            validate_identifier(table_name, "table")
        except SQLSecurityError as e:
            raise HTTPException(400, str(e))

        conn = sqlite3.connect("db/database.db")

        if not check_table_exists(conn, table_name):
            conn.close()
            raise HTTPException(404, f"Table '{table_name}' not found")

        # Count total rows
        cursor = execute_query_safely(
            conn,
            "SELECT COUNT(*) FROM {table}",
            identifier_params={'table': table_name}
        )
        total_rows = cursor.fetchone()[0]
        total_pages = max(1, math.ceil(total_rows / limit))

        # Fetch paginated data with rowid
        offset = (page - 1) * limit
        cursor = execute_query_safely(
            conn,
            "SELECT rowid, * FROM {table} LIMIT ? OFFSET ?",
            params=(limit, offset),
            identifier_params={'table': table_name}
        )
        raw_columns = [desc[0] for desc in cursor.description]
        # First column is always rowid from "SELECT rowid, *"
        # Rename it explicitly to avoid conflicts with INTEGER PRIMARY KEY aliases
        raw_columns[0] = 'rowid'
        # Deduplicate: skip any subsequent column that duplicates 'rowid'
        columns = []
        seen_rowid = False
        col_indices = []
        for i, col in enumerate(raw_columns):
            if col == 'rowid':
                if not seen_rowid:
                    seen_rowid = True
                    columns.append(col)
                    col_indices.append(i)
                # skip duplicate rowid columns
            else:
                columns.append(col)
                col_indices.append(i)

        raw_rows = cursor.fetchall()

        rows = []
        for raw_row in raw_rows:
            row = {}
            for idx, col in zip(col_indices, columns):
                row[col] = raw_row[idx]
            rows.append(row)

        conn.close()

        return TablePreviewResponse(
            columns=columns,
            rows=rows,
            total_rows=total_rows,
            page=page,
            limit=limit,
            total_pages=total_pages
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Table preview failed: {str(e)}")
        logger.error(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
        raise HTTPException(500, f"Error fetching table preview: {str(e)}")


@app.patch("/api/table/{table_name}/row", response_model=RowUpdateResponse)
async def update_row(table_name: str, request: RowUpdateRequest) -> RowUpdateResponse:
    """Update a single cell in a table row"""
    try:
        try:
            validate_identifier(table_name, "table")
            validate_identifier(request.column, "column")
        except SQLSecurityError as e:
            raise HTTPException(400, str(e))

        conn = sqlite3.connect("db/database.db")

        if not check_table_exists(conn, table_name):
            conn.close()
            raise HTTPException(404, f"Table '{table_name}' not found")

        execute_query_safely(
            conn,
            "UPDATE {table} SET {column} = ? WHERE rowid = ?",
            params=(request.value, request.rowid),
            identifier_params={'table': table_name, 'column': request.column}
        )
        conn.commit()
        conn.close()

        logger.info(f"[SUCCESS] Row updated: table={table_name}, rowid={request.rowid}, column={request.column}")
        return RowUpdateResponse(success=True)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Row update failed: {str(e)}")
        logger.error(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
        raise HTTPException(500, f"Error updating row: {str(e)}")


@app.post("/api/table/{table_name}/row", response_model=RowInsertResponse)
async def insert_row(table_name: str, request: RowInsertRequest) -> RowInsertResponse:
    """Insert a new row into a table"""
    try:
        try:
            validate_identifier(table_name, "table")
            for col_name in request.values.keys():
                validate_identifier(col_name, "column")
        except SQLSecurityError as e:
            raise HTTPException(400, str(e))

        conn = sqlite3.connect("db/database.db")

        if not check_table_exists(conn, table_name):
            conn.close()
            raise HTTPException(404, f"Table '{table_name}' not found")

        columns = list(request.values.keys())
        values = list(request.values.values())
        col_placeholders = ", ".join(f"{{{f'col{i}'}}}" for i in range(len(columns)))
        val_placeholders = ", ".join("?" for _ in values)

        identifier_params = {f'col{i}': col for i, col in enumerate(columns)}
        identifier_params['table'] = table_name

        query = f"INSERT INTO {{table}} ({col_placeholders}) VALUES ({val_placeholders})"
        cursor = execute_query_safely(
            conn,
            query,
            params=tuple(values),
            identifier_params=identifier_params
        )
        conn.commit()
        new_rowid = cursor.lastrowid
        conn.close()

        logger.info(f"[SUCCESS] Row inserted: table={table_name}, rowid={new_rowid}")
        return RowInsertResponse(success=True, rowid=new_rowid)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Row insert failed: {str(e)}")
        logger.error(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
        raise HTTPException(500, f"Error inserting row: {str(e)}")


@app.delete("/api/table/{table_name}/row/{rowid}")
async def delete_row(table_name: str, rowid: int) -> RowDeleteResponse:
    """Delete a row from a table by rowid"""
    try:
        try:
            validate_identifier(table_name, "table")
        except SQLSecurityError as e:
            raise HTTPException(400, str(e))

        if rowid < 1:
            raise HTTPException(400, "rowid must be a positive integer")

        conn = sqlite3.connect("db/database.db")

        if not check_table_exists(conn, table_name):
            conn.close()
            raise HTTPException(404, f"Table '{table_name}' not found")

        execute_query_safely(
            conn,
            "DELETE FROM {table} WHERE rowid = ?",
            params=(rowid,),
            identifier_params={'table': table_name}
        )
        conn.commit()
        conn.close()

        logger.info(f"[SUCCESS] Row deleted: table={table_name}, rowid={rowid}")
        return RowDeleteResponse(success=True)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Row delete failed: {str(e)}")
        logger.error(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
        raise HTTPException(500, f"Error deleting row: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=int(os.environ.get("BACKEND_PORT", "8000")), reload=True)