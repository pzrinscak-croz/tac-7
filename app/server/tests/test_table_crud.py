"""
Tests for the table CRUD endpoints:
- GET    /api/table/{name}/preview
- PATCH  /api/table/{name}/row
- POST   /api/table/{name}/row
- DELETE /api/table/{name}/row/{rowid}
"""

import os
import sqlite3

import pytest
from fastapi.testclient import TestClient

from server import app


@pytest.fixture
def client_with_db(tmp_path, monkeypatch):
    """
    Create a temp working directory with a db/database.db that contains
    a `users` table populated with 75 rows so pagination is meaningful.
    """
    monkeypatch.chdir(tmp_path)
    os.makedirs("db", exist_ok=True)

    conn = sqlite3.connect("db/database.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            name TEXT,
            email TEXT,
            age INTEGER
        )
        """
    )
    for i in range(1, 76):
        cursor.execute(
            "INSERT INTO users (name, email, age) VALUES (?, ?, ?)",
            (f"user_{i}", f"user_{i}@example.com", 20 + (i % 30)),
        )
    conn.commit()
    conn.close()

    with TestClient(app) as tc:
        yield tc


class TestPreviewEndpoint:
    def test_preview_first_page_returns_50_rows(self, client_with_db):
        response = client_with_db.get("/api/table/users/preview?page=1&limit=50")
        assert response.status_code == 200
        body = response.json()
        assert body["error"] is None
        assert body["table_name"] == "users"
        assert body["page"] == 1
        assert body["limit"] == 50
        assert body["total_rows"] == 75
        assert body["total_pages"] == 2
        assert len(body["rows"]) == 50
        assert "rowid" in body["rows"][0]
        assert set(body["columns"]) == {"id", "name", "email", "age"}

    def test_preview_pagination_math_and_total_pages(self, client_with_db):
        # Page 2 should have remaining 25 rows
        response = client_with_db.get("/api/table/users/preview?page=2&limit=50")
        assert response.status_code == 200
        body = response.json()
        assert body["page"] == 2
        assert body["total_pages"] == 2
        assert len(body["rows"]) == 25

    def test_preview_page_out_of_bounds_returns_empty(self, client_with_db):
        response = client_with_db.get("/api/table/users/preview?page=99&limit=50")
        assert response.status_code == 200
        body = response.json()
        assert body["rows"] == []
        assert body["total_rows"] == 75

    def test_preview_rejects_bad_identifier(self, client_with_db):
        response = client_with_db.get(
            "/api/table/users;%20DROP%20TABLE%20users/preview"
        )
        assert response.status_code == 400

    def test_preview_404_on_missing_table(self, client_with_db):
        response = client_with_db.get("/api/table/no_such_table/preview")
        assert response.status_code == 404


class TestUpdateRowEndpoint:
    def test_update_row_persists_value(self, client_with_db):
        response = client_with_db.patch(
            "/api/table/users/row",
            json={"rowid": 1, "column": "name", "value": "Edited Value"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["rowid"] == 1
        assert body["row_count"] == 75

        # Verify persisted
        conn = sqlite3.connect("db/database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM users WHERE rowid = 1")
        assert cursor.fetchone()[0] == "Edited Value"
        conn.close()

    def test_update_row_404_when_rowid_missing(self, client_with_db):
        response = client_with_db.patch(
            "/api/table/users/row",
            json={"rowid": 9999, "column": "name", "value": "ghost"},
        )
        assert response.status_code == 404

    def test_update_row_rejects_unknown_column(self, client_with_db):
        response = client_with_db.patch(
            "/api/table/users/row",
            json={"rowid": 1, "column": "no_such_col", "value": "x"},
        )
        assert response.status_code == 400

    def test_update_row_rejects_injection_column(self, client_with_db):
        response = client_with_db.patch(
            "/api/table/users/row",
            json={"rowid": 1, "column": "name; DROP TABLE users", "value": "x"},
        )
        assert response.status_code == 400

    def test_update_value_with_sql_characters_persists_verbatim(self, client_with_db):
        evil = "'; DROP TABLE users;--"
        response = client_with_db.patch(
            "/api/table/users/row",
            json={"rowid": 2, "column": "name", "value": evil},
        )
        assert response.status_code == 200
        conn = sqlite3.connect("db/database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM users WHERE rowid = 2")
        assert cursor.fetchone()[0] == evil
        # users table still exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
        )
        assert cursor.fetchone() is not None
        conn.close()


class TestInsertRowEndpoint:
    def test_insert_row_empty_creates_null_row(self, client_with_db):
        response = client_with_db.post(
            "/api/table/users/row",
            json={"values": {}},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["row_count"] == 76
        assert body["rowid"] > 0

        conn = sqlite3.connect("db/database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT name, email, age FROM users WHERE rowid = ?", (body["rowid"],))
        row = cursor.fetchone()
        assert row == (None, None, None)
        conn.close()

    def test_insert_row_with_values_persists(self, client_with_db):
        response = client_with_db.post(
            "/api/table/users/row",
            json={"values": {"name": "Inserted", "email": "i@example.com", "age": 99}},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["row_count"] == 76

        conn = sqlite3.connect("db/database.db")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name, email, age FROM users WHERE rowid = ?", (body["rowid"],)
        )
        assert cursor.fetchone() == ("Inserted", "i@example.com", 99)
        conn.close()

    def test_insert_row_rejects_bad_column(self, client_with_db):
        response = client_with_db.post(
            "/api/table/users/row",
            json={"values": {"name; DROP TABLE users": "x"}},
        )
        assert response.status_code == 400


class TestDeleteRowEndpoint:
    def test_delete_row_removes_row_and_returns_new_count(self, client_with_db):
        response = client_with_db.delete("/api/table/users/row/1")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["row_count"] == 74

        conn = sqlite3.connect("db/database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE rowid = 1")
        assert cursor.fetchone()[0] == 0
        conn.close()

    def test_delete_row_404_when_rowid_missing(self, client_with_db):
        response = client_with_db.delete("/api/table/users/row/9999")
        assert response.status_code == 404


class TestIdentifierInjection:
    def test_identifier_injection_blocked_on_all_endpoints(self, client_with_db):
        bad = "users;%20DROP%20TABLE%20users"

        # Preview
        r = client_with_db.get(f"/api/table/{bad}/preview")
        assert r.status_code == 400

        # Update
        r = client_with_db.patch(
            f"/api/table/{bad}/row",
            json={"rowid": 1, "column": "name", "value": "x"},
        )
        assert r.status_code == 400

        # Insert
        r = client_with_db.post(f"/api/table/{bad}/row", json={"values": {}})
        assert r.status_code == 400

        # Delete
        r = client_with_db.delete(f"/api/table/{bad}/row/1")
        assert r.status_code == 400

        # Underlying table still intact
        conn = sqlite3.connect("db/database.db")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
        )
        assert cursor.fetchone() is not None
        conn.close()
