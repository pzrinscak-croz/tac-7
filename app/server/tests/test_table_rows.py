"""Tests for table-row preview / mutation endpoints."""

import os
import sqlite3
import tempfile

import pytest
from fastapi.testclient import TestClient

from server import app


@pytest.fixture
def client(monkeypatch):
    """Set up an isolated working directory with a fresh db/database.db.

    The server endpoints connect to ``db/database.db`` (relative path), so we
    chdir into a temp directory and seed a small test table there.
    """
    tmp_dir = tempfile.mkdtemp()
    monkeypatch.chdir(tmp_dir)
    os.makedirs("db", exist_ok=True)

    conn = sqlite3.connect("db/database.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE users (
            id INTEGER,
            name TEXT,
            age INTEGER
        )
        """
    )
    rows = [(i, f"user_{i}", 20 + (i % 50)) for i in range(1, 76)]  # 75 rows
    cursor.executemany("INSERT INTO users (id, name, age) VALUES (?, ?, ?)", rows)
    conn.commit()
    conn.close()

    yield TestClient(app)


class TestPreview:
    def test_preview_page_1_returns_50_rows(self, client):
        resp = client.get("/api/table/users/preview?page=1&limit=50")
        assert resp.status_code == 200
        body = resp.json()
        assert body["error"] is None
        assert body["table_name"] == "users"
        assert body["columns"] == ["id", "name", "age"]
        assert body["page"] == 1
        assert body["limit"] == 50
        assert body["total_rows"] == 75
        assert body["total_pages"] == 2
        assert len(body["rows"]) == 50
        first = body["rows"][0]
        assert first["rowid"] == 1
        assert first["data"] == {"id": 1, "name": "user_1", "age": 21}

    def test_preview_page_2_returns_remaining_rows(self, client):
        resp = client.get("/api/table/users/preview?page=2&limit=50")
        assert resp.status_code == 200
        body = resp.json()
        assert body["page"] == 2
        assert len(body["rows"]) == 25
        assert body["rows"][0]["rowid"] == 51

    def test_preview_invalid_table_name_400(self, client):
        # The path "users; DROP TABLE/preview" — encode the offending name
        resp = client.get("/api/table/DROP/preview")
        assert resp.status_code == 400

    def test_preview_missing_table_404(self, client):
        resp = client.get("/api/table/nonexistent/preview")
        assert resp.status_code == 404

    def test_preview_clamps_limit(self, client):
        resp = client.get("/api/table/users/preview?page=1&limit=500")
        assert resp.status_code == 200
        body = resp.json()
        assert body["limit"] == 200

    def test_preview_clamps_page_to_min_1(self, client):
        resp = client.get("/api/table/users/preview?page=0&limit=50")
        assert resp.status_code == 200
        body = resp.json()
        assert body["page"] == 1


class TestUpdate:
    def test_update_row_persists_change(self, client):
        resp = client.patch(
            "/api/table/users/row",
            json={"rowid": 1, "updates": {"name": "Updated"}},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["rowid"] == 1
        assert body["row_count"] == 75

        # Verify in DB
        conn = sqlite3.connect("db/database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM users WHERE rowid = 1")
        assert cursor.fetchone()[0] == "Updated"
        conn.close()

    def test_update_row_multiple_columns(self, client):
        resp = client.patch(
            "/api/table/users/row",
            json={"rowid": 2, "updates": {"name": "Bob", "age": 99}},
        )
        assert resp.status_code == 200
        conn = sqlite3.connect("db/database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT name, age FROM users WHERE rowid = 2")
        name, age = cursor.fetchone()
        assert name == "Bob"
        assert age == 99
        conn.close()

    def test_update_row_rejects_unknown_column(self, client):
        resp = client.patch(
            "/api/table/users/row",
            json={"rowid": 1, "updates": {"nope_col": "x"}},
        )
        assert resp.status_code == 400

    def test_update_row_rejects_invalid_column_name(self, client):
        resp = client.patch(
            "/api/table/users/row",
            json={"rowid": 1, "updates": {"name; DROP TABLE users": "x"}},
        )
        assert resp.status_code == 400

    def test_update_row_not_found(self, client):
        resp = client.patch(
            "/api/table/users/row",
            json={"rowid": 99999, "updates": {"name": "Ghost"}},
        )
        assert resp.status_code == 404

    def test_update_empty_updates_400(self, client):
        resp = client.patch(
            "/api/table/users/row",
            json={"rowid": 1, "updates": {}},
        )
        assert resp.status_code == 400


class TestInsert:
    def test_insert_row_creates_visible_row(self, client):
        resp = client.post(
            "/api/table/users/row",
            json={"data": {"id": 999, "name": "Alice", "age": 42}},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["rowid"] is not None
        assert body["row_count"] == 76

        # Confirm appears in last page
        resp = client.get("/api/table/users/preview?page=2&limit=50")
        body = resp.json()
        assert body["total_rows"] == 76
        assert any(r["data"]["name"] == "Alice" for r in body["rows"])

    def test_insert_row_with_empty_data(self, client):
        resp = client.post("/api/table/users/row", json={"data": {}})
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["row_count"] == 76

    def test_insert_row_rejects_unknown_column(self, client):
        resp = client.post(
            "/api/table/users/row",
            json={"data": {"unknown_col": 1}},
        )
        assert resp.status_code == 400

    def test_insert_row_rejects_invalid_column_name(self, client):
        resp = client.post(
            "/api/table/users/row",
            json={"data": {"name; DROP TABLE users": "x"}},
        )
        assert resp.status_code == 400


class TestDelete:
    def test_delete_row_removes_row(self, client):
        resp = client.delete("/api/table/users/row/1")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["row_count"] == 74

        conn = sqlite3.connect("db/database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE rowid = 1")
        assert cursor.fetchone()[0] == 0
        conn.close()

    def test_delete_nonexistent_row_404(self, client):
        resp = client.delete("/api/table/users/row/99999")
        assert resp.status_code == 404


class TestSecurity:
    def test_sql_injection_in_table_name_blocked_preview(self, client):
        # FastAPI path will not match path traversal, but we test invalid identifier
        resp = client.get("/api/table/users%3B%20DROP/preview")
        # Either 400 (validation) or 404 (table not found) is acceptable;
        # crucially the table must not be dropped.
        assert resp.status_code in (400, 404)

        # Verify users table is intact
        conn = sqlite3.connect("db/database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        assert cursor.fetchone()[0] == 75
        conn.close()

    def test_sql_injection_in_update_table_name_blocked(self, client):
        resp = client.patch(
            "/api/table/users%3B%20DROP/row",
            json={"rowid": 1, "updates": {"name": "x"}},
        )
        assert resp.status_code in (400, 404)

    def test_sql_injection_in_delete_table_name_blocked(self, client):
        resp = client.delete("/api/table/users%3B%20DROP/row/1")
        assert resp.status_code in (400, 404)
