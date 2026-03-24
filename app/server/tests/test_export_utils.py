import pytest
import sqlite3
import json
import pandas as pd
from datetime import datetime
from io import StringIO
from core.export_utils import generate_csv_from_data, generate_csv_from_table, generate_json_from_data, generate_json_from_table


class TestExportUtils:
    
    def test_generate_csv_from_data_empty(self):
        """Test CSV generation with empty data"""
        result = generate_csv_from_data([], [])
        assert result == b""
        
    def test_generate_csv_from_data_with_columns_no_data(self):
        """Test CSV generation with columns but no data"""
        columns = ['id', 'name', 'value']
        result = generate_csv_from_data([], columns)
        
        # Parse the CSV to verify
        csv_str = result.decode('utf-8')
        df = pd.read_csv(StringIO(csv_str))
        
        assert list(df.columns) == columns
        assert len(df) == 0
        
    def test_generate_csv_from_data_with_data(self):
        """Test CSV generation with actual data"""
        data = [
            {'id': 1, 'name': 'Test 1', 'value': 100},
            {'id': 2, 'name': 'Test 2', 'value': 200}
        ]
        columns = ['id', 'name', 'value']
        
        result = generate_csv_from_data(data, columns)
        
        # Parse the CSV to verify
        csv_str = result.decode('utf-8')
        df = pd.read_csv(StringIO(csv_str))
        
        assert list(df.columns) == columns
        assert len(df) == 2
        assert df.iloc[0]['name'] == 'Test 1'
        assert df.iloc[1]['value'] == 200
        
    def test_generate_csv_from_data_auto_columns(self):
        """Test CSV generation with automatic column detection"""
        data = [
            {'id': 1, 'name': 'Test 1'},
            {'id': 2, 'name': 'Test 2'}
        ]
        
        result = generate_csv_from_data(data, [])
        
        # Parse the CSV to verify
        csv_str = result.decode('utf-8')
        df = pd.read_csv(StringIO(csv_str))
        
        assert 'id' in df.columns
        assert 'name' in df.columns
        assert len(df) == 2
        
    def test_generate_csv_from_data_various_types(self):
        """Test CSV generation with various data types"""
        data = [
            {'int': 1, 'float': 1.5, 'string': 'test', 'bool': True, 'none': None},
            {'int': 2, 'float': 2.5, 'string': 'test2', 'bool': False, 'none': None}
        ]
        columns = ['int', 'float', 'string', 'bool', 'none']
        
        result = generate_csv_from_data(data, columns)
        
        # Parse the CSV to verify
        csv_str = result.decode('utf-8')
        df = pd.read_csv(StringIO(csv_str))
        
        assert df.iloc[0]['int'] == 1
        assert df.iloc[0]['float'] == 1.5
        assert df.iloc[0]['string'] == 'test'
        assert df.iloc[0]['bool']
        assert pd.isna(df.iloc[0]['none'])
        
    def test_generate_csv_from_data_special_characters(self):
        """Test CSV generation with special characters"""
        data = [
            {'name': 'Test, with comma', 'desc': 'Quote "test"'},
            {'name': 'New\nline', 'desc': 'Tab\there'}
        ]
        columns = ['name', 'desc']
        
        result = generate_csv_from_data(data, columns)
        
        # Parse the CSV to verify proper escaping
        csv_str = result.decode('utf-8')
        df = pd.read_csv(StringIO(csv_str))
        
        assert df.iloc[0]['name'] == 'Test, with comma'
        assert df.iloc[0]['desc'] == 'Quote "test"'
        assert df.iloc[1]['name'] == 'New\nline'
        
    def test_generate_csv_from_data_unicode(self):
        """Test CSV generation with Unicode characters"""
        data = [
            {'name': 'Test 测试', 'emoji': '😀🎉'},
            {'name': 'Café', 'emoji': '☕'}
        ]
        columns = ['name', 'emoji']
        
        result = generate_csv_from_data(data, columns)
        
        # Parse the CSV to verify Unicode handling
        csv_str = result.decode('utf-8')
        df = pd.read_csv(StringIO(csv_str))
        
        assert df.iloc[0]['name'] == 'Test 测试'
        assert df.iloc[0]['emoji'] == '😀🎉'
        assert df.iloc[1]['name'] == 'Café'
        
    def test_generate_csv_from_table_nonexistent(self):
        """Test CSV generation from non-existent table"""
        # Create in-memory database
        conn = sqlite3.connect(':memory:')
        
        with pytest.raises(ValueError, match="Table 'nonexistent' does not exist"):
            generate_csv_from_table(conn, 'nonexistent')
            
        conn.close()
        
    def test_generate_csv_from_table_empty(self):
        """Test CSV generation from empty table"""
        # Create in-memory database with empty table
        conn = sqlite3.connect(':memory:')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                name TEXT,
                value REAL
            )
        ''')
        conn.commit()
        
        result = generate_csv_from_table(conn, 'test_table')
        
        # Parse the CSV to verify
        csv_str = result.decode('utf-8')
        df = pd.read_csv(StringIO(csv_str))
        
        assert 'id' in df.columns
        assert 'name' in df.columns
        assert 'value' in df.columns
        assert len(df) == 0
        
        conn.close()
        
    def test_generate_csv_from_table_with_data(self):
        """Test CSV generation from table with data"""
        # Create in-memory database with data
        conn = sqlite3.connect(':memory:')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                name TEXT,
                value REAL,
                created_date TEXT
            )
        ''')
        
        cursor.executemany('''
            INSERT INTO test_table (name, value, created_date) 
            VALUES (?, ?, ?)
        ''', [
            ('Item 1', 100.5, '2024-01-01'),
            ('Item 2', 200.75, '2024-01-02'),
            ('Item 3', None, '2024-01-03')
        ])
        conn.commit()
        
        result = generate_csv_from_table(conn, 'test_table')
        
        # Parse the CSV to verify
        csv_str = result.decode('utf-8')
        df = pd.read_csv(StringIO(csv_str))
        
        assert len(df) == 3
        assert df.iloc[0]['name'] == 'Item 1'
        assert df.iloc[1]['value'] == 200.75
        assert pd.isna(df.iloc[2]['value'])
        assert df.iloc[2]['created_date'] == '2024-01-03'
        
        conn.close()
        
    def test_generate_csv_from_table_special_name(self):
        """Test CSV generation from table with special characters in name"""
        # Create in-memory database
        conn = sqlite3.connect(':memory:')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE "special-table-name" (
                id INTEGER PRIMARY KEY,
                data TEXT
            )
        ''')
        
        cursor.execute('INSERT INTO "special-table-name" (data) VALUES (?)', ('test data',))
        conn.commit()
        
        result = generate_csv_from_table(conn, 'special-table-name')
        
        # Parse the CSV to verify
        csv_str = result.decode('utf-8')
        df = pd.read_csv(StringIO(csv_str))
        
        assert len(df) == 1
        assert df.iloc[0]['data'] == 'test data'

        conn.close()


class TestGenerateJsonFromData:

    def test_empty_data_and_columns(self):
        """Test JSON generation with empty data and columns returns []"""
        result = generate_json_from_data([], [])
        parsed = json.loads(result.decode('utf-8'))
        assert parsed == []

    def test_single_row_basic_types(self):
        """Test JSON generation with a single row of basic types"""
        data = [{'id': 1, 'score': 3.14, 'name': 'Alice', 'active': True, 'notes': None}]
        columns = ['id', 'score', 'name', 'active', 'notes']
        result = generate_json_from_data(data, columns)
        parsed = json.loads(result.decode('utf-8'))
        assert len(parsed) == 1
        assert parsed[0]['id'] == 1
        assert parsed[0]['score'] == 3.14
        assert parsed[0]['name'] == 'Alice'
        assert parsed[0]['active'] is True
        assert parsed[0]['notes'] is None

    def test_multiple_rows(self):
        """Test JSON generation with multiple rows returns correct structure"""
        data = [
            {'id': 1, 'name': 'Alice'},
            {'id': 2, 'name': 'Bob'},
        ]
        columns = ['id', 'name']
        result = generate_json_from_data(data, columns)
        parsed = json.loads(result.decode('utf-8'))
        assert len(parsed) == 2
        assert parsed[0] == {'id': 1, 'name': 'Alice'}
        assert parsed[1] == {'id': 2, 'name': 'Bob'}

    def test_column_filtering(self):
        """Test that only specified columns appear in the output"""
        data = [{'id': 1, 'name': 'Alice', 'secret': 'hidden'}]
        columns = ['id', 'name']
        result = generate_json_from_data(data, columns)
        parsed = json.loads(result.decode('utf-8'))
        assert 'secret' not in parsed[0]
        assert parsed[0] == {'id': 1, 'name': 'Alice'}

    def test_datetime_coerced_to_string(self):
        """Test that datetime values are coerced to strings via default=str"""
        dt = datetime(2024, 1, 15, 10, 30, 0)
        data = [{'id': 1, 'created_at': dt}]
        columns = ['id', 'created_at']
        result = generate_json_from_data(data, columns)
        parsed = json.loads(result.decode('utf-8'))
        assert isinstance(parsed[0]['created_at'], str)
        assert '2024-01-15' in parsed[0]['created_at']

    def test_unicode_characters(self):
        """Test JSON generation with Unicode characters"""
        data = [{'name': 'Café', 'emoji': '😀🎉'}, {'name': 'Test 测试', 'emoji': '☕'}]
        columns = ['name', 'emoji']
        result = generate_json_from_data(data, columns)
        parsed = json.loads(result.decode('utf-8'))
        assert parsed[0]['name'] == 'Café'
        assert parsed[0]['emoji'] == '😀🎉'
        assert parsed[1]['name'] == 'Test 测试'

    def test_auto_columns_from_data(self):
        """Test JSON generation infers columns when none are provided"""
        data = [{'a': 1, 'b': 2}]
        result = generate_json_from_data(data, [])
        parsed = json.loads(result.decode('utf-8'))
        assert parsed[0] == {'a': 1, 'b': 2}


class TestGenerateJsonFromTable:

    def test_nonexistent_table_raises_value_error(self):
        """Test that a non-existent table raises ValueError"""
        conn = sqlite3.connect(':memory:')
        with pytest.raises(ValueError, match="Table 'nonexistent' does not exist"):
            generate_json_from_table(conn, 'nonexistent')
        conn.close()

    def test_empty_table_returns_empty_array(self):
        """Test that an empty table returns a JSON array of []"""
        conn = sqlite3.connect(':memory:')
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE empty_table (id INTEGER, name TEXT)')
        conn.commit()
        result = generate_json_from_table(conn, 'empty_table')
        parsed = json.loads(result.decode('utf-8'))
        assert parsed == []
        conn.close()

    def test_table_with_data_returns_correct_json(self):
        """Test that a table with data returns correct JSON array of objects"""
        conn = sqlite3.connect(':memory:')
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE test_table (id INTEGER, name TEXT, value REAL)')
        cursor.executemany(
            'INSERT INTO test_table VALUES (?, ?, ?)',
            [(1, 'Item 1', 10.5), (2, 'Item 2', 20.0), (3, None, None)]
        )
        conn.commit()
        result = generate_json_from_table(conn, 'test_table')
        parsed = json.loads(result.decode('utf-8'))
        assert len(parsed) == 3
        assert parsed[0] == {'id': 1, 'name': 'Item 1', 'value': 10.5}
        assert parsed[2]['name'] is None
        assert parsed[2]['value'] is None
        conn.close()