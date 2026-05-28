"""
Unit tests for core/table_crud.py — row-level CRUD operations.
"""

import os
import sqlite3
import tempfile

import pytest

from core.table_crud import (
    TableCRUDError,
    delete_row,
    get_table_preview,
    insert_row,
    update_row_cell,
)


@pytest.fixture
def test_db():
    """Create a temp SQLite DB with a `widgets` table and a few rows."""
    db_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    db_file.close()

    conn = sqlite3.connect(db_file.name)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE widgets (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            qty INTEGER
        )
        """
    )
    cursor.executemany(
        "INSERT INTO widgets (name, qty) VALUES (?, ?)",
        [
            ("alpha", 1),
            ("beta", 2),
            ("gamma", 3),
            ("delta", 4),
            ("epsilon", 5),
        ],
    )
    conn.commit()
    conn.close()

    yield db_file.name

    os.unlink(db_file.name)


@pytest.fixture
def empty_db():
    """Create a temp SQLite DB with an empty `widgets` table."""
    db_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    db_file.close()

    conn = sqlite3.connect(db_file.name)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE widgets (
            id INTEGER PRIMARY KEY,
            name TEXT,
            qty INTEGER
        )
        """
    )
    conn.commit()
    conn.close()

    yield db_file.name

    os.unlink(db_file.name)


class TestGetTablePreview:
    def test_preview_returns_paginated_rows(self, test_db):
        result = get_table_preview("widgets", page=1, limit=2, db_path=test_db)
        assert len(result["rows"]) == 2
        assert result["page"] == 1
        assert result["limit"] == 2
        assert result["total_rows"] == 5

    def test_preview_includes_rowid_for_each_row(self, test_db):
        result = get_table_preview("widgets", db_path=test_db)
        for row in result["rows"]:
            assert "rowid" in row
            assert isinstance(row["rowid"], int)

    def test_preview_returns_columns_in_order(self, test_db):
        result = get_table_preview("widgets", db_path=test_db)
        assert result["columns"] == ["id", "name", "qty"]

    def test_preview_total_pages_calculation(self, test_db):
        # 5 rows, limit 2 → 3 pages
        result = get_table_preview("widgets", page=1, limit=2, db_path=test_db)
        assert result["total_pages"] == 3

        # 5 rows, limit 5 → 1 page
        result = get_table_preview("widgets", page=1, limit=5, db_path=test_db)
        assert result["total_pages"] == 1

        # 5 rows, limit 10 → 1 page
        result = get_table_preview("widgets", page=1, limit=10, db_path=test_db)
        assert result["total_pages"] == 1

    def test_preview_empty_table_has_one_page(self, empty_db):
        result = get_table_preview("widgets", db_path=empty_db)
        assert result["rows"] == []
        assert result["total_rows"] == 0
        assert result["total_pages"] == 1

    def test_preview_second_page_shows_different_rows(self, test_db):
        page1 = get_table_preview("widgets", page=1, limit=2, db_path=test_db)
        page2 = get_table_preview("widgets", page=2, limit=2, db_path=test_db)
        ids1 = {r["rowid"] for r in page1["rows"]}
        ids2 = {r["rowid"] for r in page2["rows"]}
        assert ids1.isdisjoint(ids2)

    def test_preview_invalid_table_name_raises(self, test_db):
        with pytest.raises(TableCRUDError):
            get_table_preview("widgets'; DROP TABLE widgets--", db_path=test_db)

    def test_preview_missing_table_raises(self, test_db):
        with pytest.raises(TableCRUDError):
            get_table_preview("nonexistent", db_path=test_db)

    def test_preview_page_clamped_to_minimum_one(self, test_db):
        result = get_table_preview("widgets", page=0, limit=2, db_path=test_db)
        assert result["page"] == 1

    def test_preview_limit_clamped_to_max_two_hundred(self, test_db):
        result = get_table_preview("widgets", page=1, limit=999, db_path=test_db)
        assert result["limit"] == 200


class TestUpdateRowCell:
    def test_update_cell_updates_value(self, test_db):
        result = update_row_cell("widgets", rowid=1, column="name", value="changed", db_path=test_db)
        assert result["success"] is True

        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM widgets WHERE rowid = 1")
        assert cursor.fetchone()[0] == "changed"
        conn.close()

    def test_update_cell_persists_across_connections(self, test_db):
        update_row_cell("widgets", rowid=2, column="qty", value=99, db_path=test_db)

        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()
        cursor.execute("SELECT qty FROM widgets WHERE rowid = 2")
        assert cursor.fetchone()[0] == 99
        conn.close()

    def test_update_cell_invalid_column_raises(self, test_db):
        with pytest.raises(TableCRUDError):
            update_row_cell(
                "widgets", rowid=1, column="name'; DROP TABLE widgets--", value="x", db_path=test_db
            )

    def test_update_cell_nonexistent_column_raises(self, test_db):
        with pytest.raises(TableCRUDError):
            update_row_cell("widgets", rowid=1, column="not_a_column", value="x", db_path=test_db)

    def test_update_cell_invalid_table_raises(self, test_db):
        with pytest.raises(TableCRUDError):
            update_row_cell(
                "widgets'; DROP TABLE widgets--", rowid=1, column="name", value="x", db_path=test_db
            )

    def test_update_cell_missing_rowid_returns_error(self, test_db):
        result = update_row_cell("widgets", rowid=9999, column="name", value="x", db_path=test_db)
        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_update_cell_with_null_value(self, test_db):
        result = update_row_cell("widgets", rowid=1, column="qty", value=None, db_path=test_db)
        assert result["success"] is True

        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()
        cursor.execute("SELECT qty FROM widgets WHERE rowid = 1")
        assert cursor.fetchone()[0] is None
        conn.close()


class TestInsertRow:
    def test_insert_row_with_values(self, test_db):
        result = insert_row("widgets", {"name": "zeta", "qty": 7}, db_path=test_db)
        assert result["success"] is True
        assert result["rowid"] is not None

        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name, qty FROM widgets WHERE rowid = ?", (result["rowid"],))
        row = cursor.fetchone()
        assert row[0] == "zeta"
        assert row[1] == 7
        conn.close()

    def test_insert_row_default_values(self, empty_db):
        result = insert_row("widgets", {}, db_path=empty_db)
        assert result["success"] is True
        assert result["rowid"] is not None

    def test_insert_row_returns_rowid(self, test_db):
        result = insert_row("widgets", {"name": "x"}, db_path=test_db)
        assert isinstance(result["rowid"], int)
        assert result["rowid"] > 0

    def test_insert_row_invalid_column_raises(self, test_db):
        with pytest.raises(TableCRUDError):
            insert_row("widgets", {"not_a_column": "x"}, db_path=test_db)

    def test_insert_row_injection_in_column_name_raises(self, test_db):
        with pytest.raises(TableCRUDError):
            insert_row("widgets", {"name'; DROP TABLE widgets--": "x"}, db_path=test_db)

    def test_insert_row_special_characters_in_value(self, test_db):
        result = insert_row(
            "widgets",
            {"name": "O'Reilly; DROP TABLE widgets--", "qty": 1},
            db_path=test_db,
        )
        assert result["success"] is True

        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM widgets WHERE rowid = ?", (result["rowid"],))
        assert cursor.fetchone()[0] == "O'Reilly; DROP TABLE widgets--"
        # Confirm the table is still there
        cursor.execute("SELECT COUNT(*) FROM widgets")
        assert cursor.fetchone()[0] >= 1
        conn.close()


class TestDeleteRow:
    def test_delete_row_removes_record(self, test_db):
        result = delete_row("widgets", rowid=1, db_path=test_db)
        assert result["success"] is True

        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM widgets WHERE rowid = 1")
        assert cursor.fetchone()[0] == 0
        conn.close()

    def test_delete_row_persists(self, test_db):
        delete_row("widgets", rowid=2, db_path=test_db)
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM widgets")
        assert cursor.fetchone()[0] == 4
        conn.close()

    def test_delete_row_missing_rowid_returns_error(self, test_db):
        result = delete_row("widgets", rowid=9999, db_path=test_db)
        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_delete_row_invalid_table_raises(self, test_db):
        with pytest.raises(TableCRUDError):
            delete_row("widgets'; DROP TABLE widgets--", rowid=1, db_path=test_db)
