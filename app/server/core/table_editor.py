"""
Table editor module for paginated preview and inline editing of SQLite tables.
Constructs DML queries programmatically using escape_identifier for identifiers
and parameterized ? placeholders for all values.
"""

import sqlite3
import math
import logging
from typing import Any

from .sql_security import validate_identifier, escape_identifier, SQLSecurityError

logger = logging.getLogger(__name__)

DB_PATH = "db/database.db"


def get_table_preview(table_name: str, page: int, limit: int) -> dict:
    """
    Return a paginated preview of a table including the rowid column.
    """
    try:
        validate_identifier(table_name, "table")

        if page < 1:
            return {"success": False, "error": "page must be >= 1"}
        if not (1 <= limit <= 200):
            return {"success": False, "error": "limit must be between 1 and 200"}

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        escaped_table = escape_identifier(table_name)

        # Total row count
        cursor.execute(f"SELECT COUNT(*) FROM {escaped_table}")
        total_rows = cursor.fetchone()[0]

        total_pages = math.ceil(total_rows / limit) if total_rows > 0 else 1
        offset = (page - 1) * limit

        # Fetch data with rowid
        cursor.execute(
            f"SELECT rowid, * FROM {escaped_table} LIMIT ? OFFSET ?",
            (limit, offset),
        )
        rows = cursor.fetchall()

        columns = ["rowid"] + [desc[0] for desc in cursor.description[1:]]

        conn.close()

        return {
            "columns": columns,
            "rows": [list(row) for row in rows],
            "page": page,
            "total_pages": total_pages,
            "total_rows": total_rows,
            "page_size": limit,
            "error": None,
        }

    except SQLSecurityError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"get_table_preview error: {e}")
        return {"success": False, "error": str(e)}


def update_table_row(table_name: str, rowid: int, values: dict) -> dict:
    """
    Update a single row identified by rowid.
    """
    try:
        validate_identifier(table_name, "table")

        if not isinstance(rowid, int) or rowid < 1:
            return {"success": False, "error": "rowid must be a positive integer"}

        if not values:
            return {"success": False, "error": "values must not be empty"}

        for col in values:
            validate_identifier(col, "column")

        escaped_table = escape_identifier(table_name)
        set_clauses = ", ".join(
            f"{escape_identifier(col)} = ?" for col in values
        )
        params = list(values.values()) + [rowid]

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            f"UPDATE {escaped_table} SET {set_clauses} WHERE rowid = ?",
            params,
        )
        conn.commit()
        conn.close()

        return {"success": True, "row_count": None}

    except SQLSecurityError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"update_table_row error: {e}")
        return {"success": False, "error": str(e)}


def insert_table_row(table_name: str, values: dict) -> dict:
    """
    Insert a new row into the table. Uses DEFAULT VALUES when values is empty.
    """
    try:
        validate_identifier(table_name, "table")

        for col in values:
            validate_identifier(col, "column")

        escaped_table = escape_identifier(table_name)

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        if values:
            col_list = ", ".join(escape_identifier(col) for col in values)
            placeholders = ", ".join("?" for _ in values)
            cursor.execute(
                f"INSERT INTO {escaped_table} ({col_list}) VALUES ({placeholders})",
                list(values.values()),
            )
        else:
            cursor.execute(f"INSERT INTO {escaped_table} DEFAULT VALUES")

        conn.commit()

        cursor.execute(f"SELECT COUNT(*) FROM {escaped_table}")
        new_total = cursor.fetchone()[0]
        conn.close()

        return {"success": True, "row_count": new_total}

    except SQLSecurityError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"insert_table_row error: {e}")
        return {"success": False, "error": str(e)}


def delete_table_row(table_name: str, rowid: int) -> dict:
    """
    Delete a single row identified by rowid.
    """
    try:
        validate_identifier(table_name, "table")

        if not isinstance(rowid, int) or rowid < 1:
            return {"success": False, "error": "rowid must be a positive integer"}

        escaped_table = escape_identifier(table_name)

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            f"DELETE FROM {escaped_table} WHERE rowid = ?",
            (rowid,),
        )
        conn.commit()

        cursor.execute(f"SELECT COUNT(*) FROM {escaped_table}")
        new_total = cursor.fetchone()[0]
        conn.close()

        return {"success": True, "row_count": new_total}

    except SQLSecurityError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"delete_table_row error: {e}")
        return {"success": False, "error": str(e)}
