"""
Unit tests for the table_editor module.
Uses a temporary SQLite file to test all four CRUD operations.
"""

import pytest
import sqlite3

import core.table_editor as table_editor


@pytest.fixture
def test_db(tmp_path):
    """Create a temp SQLite DB with a test table containing 5 rows."""
    db_file = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_file))
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE items (
            name TEXT NOT NULL,
            value INTEGER
        )
        """
    )
    for i in range(1, 6):
        cursor.execute(
            "INSERT INTO items (name, value) VALUES (?, ?)",
            (f"item{i}", i * 10),
        )
    conn.commit()
    conn.close()
    return str(db_file)


@pytest.fixture(autouse=True)
def patch_db_path(test_db, monkeypatch):
    """Redirect table_editor.DB_PATH to the temp database."""
    monkeypatch.setattr(table_editor, "DB_PATH", test_db)


# ---------------------------------------------------------------------------
# get_table_preview
# ---------------------------------------------------------------------------

class TestGetTablePreview:
    def test_first_page(self):
        result = table_editor.get_table_preview("items", page=1, limit=3)
        assert result["error"] is None
        assert result["total_rows"] == 5
        assert result["total_pages"] == 2
        assert result["page"] == 1
        assert len(result["rows"]) == 3
        assert "rowid" in result["columns"]
        assert "name" in result["columns"]
        assert "value" in result["columns"]

    def test_second_page(self):
        first = table_editor.get_table_preview("items", page=1, limit=3)
        second = table_editor.get_table_preview("items", page=2, limit=3)
        assert second["error"] is None
        assert len(second["rows"]) == 2
        # First rows of page 1 and page 2 should differ
        assert first["rows"][0] != second["rows"][0]

    def test_invalid_table_name(self):
        result = table_editor.get_table_preview("'; DROP TABLE items; --", page=1, limit=50)
        assert result["success"] is False
        assert result["error"] is not None

    def test_page_beyond_total(self):
        result = table_editor.get_table_preview("items", page=100, limit=50)
        assert result["error"] is None
        assert result["rows"] == []
        assert result["total_rows"] == 5

    def test_invalid_limit_zero(self):
        result = table_editor.get_table_preview("items", page=1, limit=0)
        assert result["success"] is False

    def test_invalid_limit_too_large(self):
        result = table_editor.get_table_preview("items", page=1, limit=201)
        assert result["success"] is False

    def test_invalid_page(self):
        result = table_editor.get_table_preview("items", page=0, limit=10)
        assert result["success"] is False


# ---------------------------------------------------------------------------
# update_table_row
# ---------------------------------------------------------------------------

class TestUpdateTableRow:
    def test_update_value(self, test_db):
        # Fetch rowid of the first row
        conn = sqlite3.connect(test_db)
        row = conn.execute("SELECT rowid FROM items LIMIT 1").fetchone()
        conn.close()
        rowid = row[0]

        result = table_editor.update_table_row("items", rowid, {"name": "updated"})
        assert result["success"] is True

        conn = sqlite3.connect(test_db)
        updated = conn.execute(
            "SELECT name FROM items WHERE rowid = ?", (rowid,)
        ).fetchone()
        conn.close()
        assert updated[0] == "updated"

    def test_invalid_column_name(self):
        result = table_editor.update_table_row("items", 1, {"SELECT": "bad"})
        assert result["success"] is False
        assert result["error"] is not None

    def test_invalid_rowid_zero(self):
        result = table_editor.update_table_row("items", 0, {"name": "x"})
        assert result["success"] is False

    def test_invalid_rowid_negative(self):
        result = table_editor.update_table_row("items", -5, {"name": "x"})
        assert result["success"] is False

    def test_empty_values(self):
        result = table_editor.update_table_row("items", 1, {})
        assert result["success"] is False


# ---------------------------------------------------------------------------
# insert_table_row
# ---------------------------------------------------------------------------

class TestInsertTableRow:
    def test_insert_row(self):
        result = table_editor.insert_table_row("items", {"name": "new_item", "value": 99})
        assert result["success"] is True
        assert result["row_count"] == 6

    def test_insert_empty_values(self):
        # items.name has NOT NULL — SQLite should raise an error for DEFAULT VALUES
        result = table_editor.insert_table_row("items", {})
        assert result["success"] is False
        assert result["error"] is not None

    def test_insert_increases_count(self, test_db):
        conn = sqlite3.connect(test_db)
        before = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
        conn.close()

        result = table_editor.insert_table_row("items", {"name": "extra", "value": 0})
        assert result["success"] is True
        assert result["row_count"] == before + 1


# ---------------------------------------------------------------------------
# delete_table_row
# ---------------------------------------------------------------------------

class TestDeleteTableRow:
    def test_delete_row(self, test_db):
        conn = sqlite3.connect(test_db)
        row = conn.execute("SELECT rowid FROM items LIMIT 1").fetchone()
        conn.close()
        rowid = row[0]

        result = table_editor.delete_table_row("items", rowid)
        assert result["success"] is True
        assert result["row_count"] == 4

    def test_delete_nonexistent_rowid(self):
        result = table_editor.delete_table_row("items", 9999)
        assert result["success"] is True
        assert result["row_count"] == 5  # nothing changed

    def test_invalid_rowid_string(self):
        result = table_editor.delete_table_row("items", "not_an_int")  # type: ignore
        assert result["success"] is False

    def test_invalid_rowid_zero(self):
        result = table_editor.delete_table_row("items", 0)
        assert result["success"] is False

    def test_invalid_table_name(self):
        result = table_editor.delete_table_row("'; DROP TABLE items; --", 1)
        assert result["success"] is False
