"""
Row-level CRUD operations for SQLite tables backing the preview/edit feature.
All operations route through sql_security for identifier validation and
parameterized value binding.
"""

import math
import sqlite3
from typing import Any, Dict, List, Optional

from .sql_security import (
    SQLSecurityError,
    check_table_exists,
    escape_identifier,
    execute_query_safely,
    validate_identifier,
)


DEFAULT_DB_PATH = "db/database.db"


class TableCRUDError(Exception):
    """Raised when a CRUD precondition fails (missing table, bad identifier, etc.)."""

    pass


def _get_column_names(conn: sqlite3.Connection, table_name: str) -> List[str]:
    cursor = execute_query_safely(
        conn,
        "PRAGMA table_info({table})",
        identifier_params={"table": table_name},
    )
    return [row[1] for row in cursor.fetchall()]


def _open_validated(table_name: str, db_path: str) -> sqlite3.Connection:
    try:
        validate_identifier(table_name, "table")
    except SQLSecurityError as e:
        raise TableCRUDError(str(e))

    conn = sqlite3.connect(db_path)
    if not check_table_exists(conn, table_name):
        conn.close()
        raise TableCRUDError(f"Table '{table_name}' not found")
    return conn


def get_table_preview(
    table_name: str,
    page: int = 1,
    limit: int = 50,
    db_path: str = DEFAULT_DB_PATH,
) -> Dict[str, Any]:
    """Return a single page of rows from the given table, including rowid."""
    page = max(1, int(page))
    limit = max(1, min(200, int(limit)))

    conn = _open_validated(table_name, db_path)
    try:
        conn.row_factory = sqlite3.Row

        count_cursor = execute_query_safely(
            conn,
            "SELECT COUNT(*) FROM {table}",
            identifier_params={"table": table_name},
        )
        total_rows = count_cursor.fetchone()[0]
        total_pages = max(1, math.ceil(total_rows / limit)) if total_rows else 1

        columns = _get_column_names(conn, table_name)

        offset = (page - 1) * limit
        rows_cursor = execute_query_safely(
            conn,
            "SELECT rowid AS __rowid__, * FROM {table} LIMIT ? OFFSET ?",
            params=(limit, offset),
            identifier_params={"table": table_name},
        )
        raw_rows = rows_cursor.fetchall()

        rows: List[Dict[str, Any]] = []
        for raw in raw_rows:
            row_dict = dict(raw)
            rowid = row_dict.pop("__rowid__")
            values = {col: row_dict.get(col) for col in columns}
            rows.append({"rowid": rowid, "values": values})

        return {
            "columns": columns,
            "rows": rows,
            "page": page,
            "limit": limit,
            "total_rows": total_rows,
            "total_pages": total_pages,
        }
    finally:
        conn.close()


def update_row_cell(
    table_name: str,
    rowid: int,
    column: str,
    value: Any,
    db_path: str = DEFAULT_DB_PATH,
) -> Dict[str, Any]:
    """Update a single cell in a row, identified by rowid + column name."""
    try:
        validate_identifier(column, "column")
    except SQLSecurityError as e:
        raise TableCRUDError(str(e))

    conn = _open_validated(table_name, db_path)
    try:
        existing_columns = _get_column_names(conn, table_name)
        if column not in existing_columns:
            raise TableCRUDError(
                f"Column '{column}' does not exist in table '{table_name}'"
            )

        cursor = execute_query_safely(
            conn,
            "UPDATE {table} SET {column} = ? WHERE rowid = ?",
            params=(value, rowid),
            identifier_params={"table": table_name, "column": column},
        )
        if cursor.rowcount == 0:
            return {"success": False, "error": "Row not found"}

        conn.commit()
        return {"success": True, "rowid": rowid}
    finally:
        conn.close()


def insert_row(
    table_name: str,
    values: Optional[Dict[str, Any]] = None,
    db_path: str = DEFAULT_DB_PATH,
) -> Dict[str, Any]:
    """Insert a new row. If values is empty, use DEFAULT VALUES."""
    values = values or {}

    conn = _open_validated(table_name, db_path)
    try:
        existing_columns = _get_column_names(conn, table_name)

        if not values:
            cursor = execute_query_safely(
                conn,
                "INSERT INTO {table} DEFAULT VALUES",
                identifier_params={"table": table_name},
            )
        else:
            for col in values.keys():
                try:
                    validate_identifier(col, "column")
                except SQLSecurityError as e:
                    raise TableCRUDError(str(e))
                if col not in existing_columns:
                    raise TableCRUDError(
                        f"Column '{col}' does not exist in table '{table_name}'"
                    )

            column_keys = list(values.keys())
            escaped_cols = ", ".join(escape_identifier(c) for c in column_keys)
            placeholders = ", ".join(["?"] * len(column_keys))
            value_tuple = tuple(values[c] for c in column_keys)

            cursor = execute_query_safely(
                conn,
                f"INSERT INTO {{table}} ({escaped_cols}) VALUES ({placeholders})",
                params=value_tuple,
                identifier_params={"table": table_name},
            )

        conn.commit()
        return {"success": True, "rowid": cursor.lastrowid}
    finally:
        conn.close()


def delete_row(
    table_name: str,
    rowid: int,
    db_path: str = DEFAULT_DB_PATH,
) -> Dict[str, Any]:
    """Delete a row by its SQLite rowid."""
    conn = _open_validated(table_name, db_path)
    try:
        cursor = execute_query_safely(
            conn,
            "DELETE FROM {table} WHERE rowid = ?",
            params=(rowid,),
            identifier_params={"table": table_name},
        )
        if cursor.rowcount == 0:
            return {"success": False, "error": "Row not found"}

        conn.commit()
        return {"success": True, "rowid": rowid}
    finally:
        conn.close()
