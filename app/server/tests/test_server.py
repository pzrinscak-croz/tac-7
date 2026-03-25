import pytest
import os
import sqlite3
import tempfile
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# Save real sqlite3.connect BEFORE any patching so lambdas can use it
_real_sqlite3_connect = sqlite3.connect

# Temp DB for insert tests
DB_TEMP = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
DB_PATH = DB_TEMP.name
DB_TEMP.close()


def _setup_test_db(path: str):
    conn = _real_sqlite3_connect(path)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS users (id INTEGER, name TEXT, email TEXT, age INTEGER)"
    )
    conn.executemany(
        "INSERT INTO users VALUES (?, ?, ?, ?)",
        [(i, f"User{i}", f"user{i}@example.com", 20 + i) for i in range(1, 11)],
    )
    conn.commit()
    conn.close()


class TestGenerateRandomDataEndpoint:
    """Integration tests for POST /api/generate-random-data"""

    @pytest.fixture(autouse=True)
    def setup_db(self):
        _setup_test_db(DB_PATH)
        yield
        conn = _real_sqlite3_connect(DB_PATH)
        conn.execute("DROP TABLE IF EXISTS users")
        conn.commit()
        conn.close()

    def test_returns_400_for_invalid_table_name(self):
        from server import app
        client = TestClient(app)
        response = client.post(
            "/api/generate-random-data",
            json={"table_name": "1invalid; DROP TABLE users--"}
        )
        assert response.status_code == 400

    def test_returns_404_for_nonexistent_table(self):
        from server import app
        with patch("server.check_table_exists", return_value=False), \
             patch("server.sqlite3.connect", side_effect=lambda p: _real_sqlite3_connect(DB_PATH)):
            client = TestClient(app)
            response = client.post(
                "/api/generate-random-data",
                json={"table_name": "nonexistent_table"}
            )
        assert response.status_code == 404

    def test_returns_error_when_table_is_empty(self):
        from server import app
        with patch("server.check_table_exists", return_value=True), \
             patch("server.sqlite3.connect", side_effect=lambda p: _real_sqlite3_connect(DB_PATH)), \
             patch("server.get_database_schema", return_value={
                 "tables": {"users": {"columns": {"id": "INTEGER", "name": "TEXT"}, "row_count": 0}}
             }), \
             patch("server.sample_random_rows", return_value=[]):
            client = TestClient(app)
            response = client.post(
                "/api/generate-random-data",
                json={"table_name": "users"}
            )
        assert response.status_code == 200
        data = response.json()
        assert data["rows_added"] == 0
        assert "at least 1 row" in data["error"]

    def test_returns_rows_added_on_success(self):
        from server import app

        generated = [{"id": 100 + i, "name": f"Gen{i}", "email": f"gen{i}@x.com", "age": 25} for i in range(10)]

        with patch("server.check_table_exists", return_value=True), \
             patch("server.get_database_schema", return_value={
                 "tables": {"users": {"columns": {"id": "INTEGER", "name": "TEXT", "email": "TEXT", "age": "INTEGER"}, "row_count": 10}}
             }), \
             patch("server.sample_random_rows", return_value=[{"id": 1, "name": "Alice", "email": "a@x.com", "age": 30}]), \
             patch("server.generate_random_data", return_value=generated), \
             patch("server.sqlite3.connect", side_effect=lambda p: _real_sqlite3_connect(DB_PATH)):
            client = TestClient(app)
            response = client.post(
                "/api/generate-random-data",
                json={"table_name": "users"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["rows_added"] == 10
        assert data.get("error") is None

    def test_handles_llm_malformed_json_gracefully(self):
        from server import app

        with patch("server.check_table_exists", return_value=True), \
             patch("server.sqlite3.connect", side_effect=lambda p: _real_sqlite3_connect(DB_PATH)), \
             patch("server.get_database_schema", return_value={
                 "tables": {"users": {"columns": {"id": "INTEGER"}, "row_count": 5}}
             }), \
             patch("server.sample_random_rows", return_value=[{"id": 1}]), \
             patch("server.generate_random_data", side_effect=Exception("invalid JSON returned by LLM")):
            client = TestClient(app)
            response = client.post(
                "/api/generate-random-data",
                json={"table_name": "users"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["rows_added"] == 0
        assert data["error"] is not None
