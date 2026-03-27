"""
Tests for table preview and inline editing API endpoints.
"""

import pytest
import sqlite3
import tempfile
import os
from unittest.mock import patch
from fastapi.testclient import TestClient


_real_sqlite3_connect = sqlite3.connect


@pytest.fixture
def test_db():
    """Create a test database with sample data"""
    db_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    db_file.close()

    conn = _real_sqlite3_connect(db_file.name)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE test_users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT,
            age INTEGER
        )
    ''')

    # Insert 60 rows to test pagination
    for i in range(1, 61):
        cursor.execute(
            "INSERT INTO test_users (name, email, age) VALUES (?, ?, ?)",
            (f'User{i}', f'user{i}@example.com', 20 + (i % 40))
        )

    cursor.execute('''
        CREATE TABLE empty_table (
            id INTEGER PRIMARY KEY,
            value TEXT
        )
    ''')

    conn.commit()
    conn.close()

    yield db_file.name

    os.unlink(db_file.name)


@pytest.fixture
def client(test_db):
    """Create a test client with mocked database path"""
    with patch('server.sqlite3.connect', lambda _: _real_sqlite3_connect(test_db)):
        from server import app
        with TestClient(app) as c:
            yield c


class TestTablePreview:
    """Test GET /api/table/{name}/preview"""

    def test_preview_returns_data(self, client):
        response = client.get("/api/table/test_users/preview")
        assert response.status_code == 200
        data = response.json()
        assert "columns" in data
        assert "rows" in data
        assert data["total_rows"] == 60
        assert data["page"] == 1
        assert data["limit"] == 50
        assert len(data["rows"]) == 50
        assert "rowid" in data["columns"]

    def test_preview_pagination_page2(self, client):
        response = client.get("/api/table/test_users/preview?page=2&limit=50")
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["total_pages"] == 2
        assert len(data["rows"]) == 10  # 60 - 50 = 10 remaining

    def test_preview_total_pages(self, client):
        response = client.get("/api/table/test_users/preview?limit=50")
        data = response.json()
        assert data["total_pages"] == 2  # ceil(60/50)

    def test_preview_empty_table(self, client):
        response = client.get("/api/table/empty_table/preview")
        assert response.status_code == 200
        data = response.json()
        assert data["total_rows"] == 0
        assert len(data["rows"]) == 0
        assert data["total_pages"] == 1

    def test_preview_invalid_table_name(self, client):
        response = client.get("/api/table/users'; DROP TABLE users;--/preview")
        assert response.status_code == 400

    def test_preview_nonexistent_table(self, client):
        response = client.get("/api/table/nonexistent_table/preview")
        assert response.status_code == 404


class TestRowUpdate:
    """Test PATCH /api/table/{name}/row"""

    def test_update_cell(self, client):
        response = client.patch(
            "/api/table/test_users/row",
            json={"column": "name", "value": "UpdatedName", "rowid": 1}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify the update persisted
        preview = client.get("/api/table/test_users/preview").json()
        row = next(r for r in preview["rows"] if r["rowid"] == 1)
        assert row["name"] == "UpdatedName"

    def test_update_invalid_table(self, client):
        response = client.patch(
            "/api/table/users'; DROP TABLE users;--/row",
            json={"column": "name", "value": "test", "rowid": 1}
        )
        assert response.status_code == 400

    def test_update_invalid_column(self, client):
        response = client.patch(
            "/api/table/test_users/row",
            json={"column": "name'; DROP TABLE users;--", "value": "test", "rowid": 1}
        )
        assert response.status_code == 400

    def test_update_nonexistent_table(self, client):
        response = client.patch(
            "/api/table/nonexistent_table/row",
            json={"column": "name", "value": "test", "rowid": 1}
        )
        assert response.status_code == 404


class TestRowInsert:
    """Test POST /api/table/{name}/row"""

    def test_insert_row(self, client):
        response = client.post(
            "/api/table/test_users/row",
            json={"values": {"name": "NewUser", "email": "new@example.com", "age": 25}}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["rowid"] > 0

    def test_insert_increases_count(self, client):
        before = client.get("/api/table/test_users/preview").json()["total_rows"]
        client.post(
            "/api/table/test_users/row",
            json={"values": {"name": "Another"}}
        )
        after = client.get("/api/table/test_users/preview").json()["total_rows"]
        assert after == before + 1

    def test_insert_invalid_table(self, client):
        response = client.post(
            "/api/table/users'; DROP TABLE users;--/row",
            json={"values": {"name": "test"}}
        )
        assert response.status_code == 400

    def test_insert_invalid_column(self, client):
        response = client.post(
            "/api/table/test_users/row",
            json={"values": {"name'; DROP TABLE users;--": "test"}}
        )
        assert response.status_code == 400

    def test_insert_nonexistent_table(self, client):
        response = client.post(
            "/api/table/nonexistent_table/row",
            json={"values": {"name": "test"}}
        )
        assert response.status_code == 404


class TestRowDelete:
    """Test DELETE /api/table/{name}/row/{rowid}"""

    def test_delete_row(self, client):
        response = client.delete("/api/table/test_users/row/1")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_delete_decreases_count(self, client):
        before = client.get("/api/table/test_users/preview").json()["total_rows"]
        client.delete("/api/table/test_users/row/2")
        after = client.get("/api/table/test_users/preview").json()["total_rows"]
        assert after == before - 1

    def test_delete_invalid_table(self, client):
        response = client.delete("/api/table/users'; DROP TABLE users;--/row/1")
        assert response.status_code == 400

    def test_delete_nonexistent_table(self, client):
        response = client.delete("/api/table/nonexistent_table/row/1")
        assert response.status_code == 404


class TestSQLInjectionPrevention:
    """Test SQL injection attempts on new endpoints"""

    def test_preview_injection_via_table_name(self, client):
        response = client.get("/api/table/users UNION SELECT * FROM sqlite_master/preview")
        assert response.status_code in (400, 422)

    def test_update_injection_via_column(self, client):
        response = client.patch(
            "/api/table/test_users/row",
            json={"column": "name = 'hacked' WHERE 1=1; --", "value": "x", "rowid": 1}
        )
        assert response.status_code == 400

    def test_insert_injection_via_column(self, client):
        response = client.post(
            "/api/table/test_users/row",
            json={"values": {"name) VALUES ('hacked'); --": "x"}}
        )
        assert response.status_code == 400
