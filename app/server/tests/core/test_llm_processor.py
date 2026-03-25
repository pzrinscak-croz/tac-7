import pytest
import os
import json
from unittest.mock import patch, MagicMock
from core.llm_processor import (
    generate_sql_with_openai,
    generate_sql_with_anthropic,
    format_schema_for_prompt,
    generate_sql,
    generate_random_data_with_openai,
    generate_random_data_with_anthropic,
    generate_random_data,
)
from core.data_models import QueryRequest


class TestLLMProcessor:
    
    @patch('core.llm_processor.OpenAI')
    def test_generate_sql_with_openai_success(self, mock_openai_class):
        # Mock OpenAI client and response
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "SELECT * FROM users WHERE age > 25"
        mock_client.chat.completions.create.return_value = mock_response
        
        # Mock environment variable
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            query_text = "Show me users older than 25"
            schema_info = {
                'tables': {
                    'users': {
                        'columns': {'id': 'INTEGER', 'name': 'TEXT', 'age': 'INTEGER'},
                        'row_count': 100
                    }
                }
            }
            
            result = generate_sql_with_openai(query_text, schema_info)
            
            assert result == "SELECT * FROM users WHERE age > 25"
            mock_client.chat.completions.create.assert_called_once()
            
            # Verify the API call parameters
            call_args = mock_client.chat.completions.create.call_args
            assert call_args[1]['model'] == 'gpt-4.1-2025-04-14'
            assert call_args[1]['temperature'] == 0.1
            assert call_args[1]['max_tokens'] == 500
    
    @patch('core.llm_processor.OpenAI')
    def test_generate_sql_with_openai_clean_markdown(self, mock_openai_class):
        # Test SQL cleanup from markdown
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "```sql\nSELECT * FROM users\n```"
        mock_client.chat.completions.create.return_value = mock_response
        
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            query_text = "Show all users"
            schema_info = {'tables': {}}
            
            result = generate_sql_with_openai(query_text, schema_info)
            
            assert result == "SELECT * FROM users"
    
    def test_generate_sql_with_openai_no_api_key(self):
        # Test error when API key is not set
        with patch.dict(os.environ, {}, clear=True):
            query_text = "Show all users"
            schema_info = {'tables': {}}
            
            with pytest.raises(Exception) as exc_info:
                generate_sql_with_openai(query_text, schema_info)
            
            assert "OPENAI_API_KEY environment variable not set" in str(exc_info.value)
    
    @patch('core.llm_processor.OpenAI')
    def test_generate_sql_with_openai_api_error(self, mock_openai_class):
        # Test API error handling
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            query_text = "Show all users"
            schema_info = {'tables': {}}
            
            with pytest.raises(Exception) as exc_info:
                generate_sql_with_openai(query_text, schema_info)
            
            assert "Error generating SQL with OpenAI" in str(exc_info.value)
    
    @patch('core.llm_processor.Anthropic')
    def test_generate_sql_with_anthropic_success(self, mock_anthropic_class):
        # Mock Anthropic client and response
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.content[0].text = "SELECT * FROM products WHERE price < 100"
        mock_client.messages.create.return_value = mock_response
        
        # Mock environment variable
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}):
            query_text = "Show me products under $100"
            schema_info = {
                'tables': {
                    'products': {
                        'columns': {'id': 'INTEGER', 'name': 'TEXT', 'price': 'REAL'},
                        'row_count': 50
                    }
                }
            }
            
            result = generate_sql_with_anthropic(query_text, schema_info)
            
            assert result == "SELECT * FROM products WHERE price < 100"
            mock_client.messages.create.assert_called_once()
            
            # Verify the API call parameters
            call_args = mock_client.messages.create.call_args
            assert call_args[1]['model'] == 'claude-sonnet-4-0'
            assert call_args[1]['temperature'] == 0.1
            assert call_args[1]['max_tokens'] == 500
    
    @patch('core.llm_processor.Anthropic')
    def test_generate_sql_with_anthropic_clean_markdown(self, mock_anthropic_class):
        # Test SQL cleanup from markdown
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.content[0].text = "```\nSELECT * FROM orders\n```"
        mock_client.messages.create.return_value = mock_response
        
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}):
            query_text = "Show all orders"
            schema_info = {'tables': {}}
            
            result = generate_sql_with_anthropic(query_text, schema_info)
            
            assert result == "SELECT * FROM orders"
    
    def test_generate_sql_with_anthropic_no_api_key(self):
        # Test error when API key is not set
        with patch.dict(os.environ, {}, clear=True):
            query_text = "Show all orders"
            schema_info = {'tables': {}}
            
            with pytest.raises(Exception) as exc_info:
                generate_sql_with_anthropic(query_text, schema_info)
            
            assert "ANTHROPIC_API_KEY environment variable not set" in str(exc_info.value)
    
    @patch('core.llm_processor.Anthropic')
    def test_generate_sql_with_anthropic_api_error(self, mock_anthropic_class):
        # Test API error handling
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client
        mock_client.messages.create.side_effect = Exception("API Error")
        
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}):
            query_text = "Show all orders"
            schema_info = {'tables': {}}
            
            with pytest.raises(Exception) as exc_info:
                generate_sql_with_anthropic(query_text, schema_info)
            
            assert "Error generating SQL with Anthropic" in str(exc_info.value)
    
    def test_format_schema_for_prompt(self):
        # Test schema formatting for LLM prompt
        schema_info = {
            'tables': {
                'users': {
                    'columns': {'id': 'INTEGER', 'name': 'TEXT', 'age': 'INTEGER'},
                    'row_count': 100
                },
                'products': {
                    'columns': {'id': 'INTEGER', 'name': 'TEXT', 'price': 'REAL'},
                    'row_count': 50
                }
            }
        }
        
        result = format_schema_for_prompt(schema_info)
        
        assert "Table: users" in result
        assert "Table: products" in result
        assert "- id (INTEGER)" in result
        assert "- name (TEXT)" in result
        assert "- age (INTEGER)" in result
        assert "- price (REAL)" in result
        assert "Row count: 100" in result
        assert "Row count: 50" in result
    
    def test_format_schema_for_prompt_empty(self):
        # Test with empty schema
        schema_info = {'tables': {}}
        
        result = format_schema_for_prompt(schema_info)
        
        assert result == ""
    
    @patch('core.llm_processor.generate_sql_with_openai')
    def test_generate_sql_openai_key_priority(self, mock_openai_func):
        # Test that OpenAI is used when OpenAI key exists (regardless of request preference)
        mock_openai_func.return_value = "SELECT * FROM users"
        
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'openai-key', 'ANTHROPIC_API_KEY': 'anthropic-key'}):
            request = QueryRequest(query="Show all users", llm_provider="anthropic")
            schema_info = {'tables': {}}
            
            result = generate_sql(request, schema_info)
            
            assert result == "SELECT * FROM users"
            mock_openai_func.assert_called_once_with("Show all users", schema_info)
    
    @patch('core.llm_processor.generate_sql_with_anthropic')
    def test_generate_sql_anthropic_fallback(self, mock_anthropic_func):
        # Test that Anthropic is used when only Anthropic key exists
        mock_anthropic_func.return_value = "SELECT * FROM products"
        
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'anthropic-key'}, clear=True):
            request = QueryRequest(query="Show all products", llm_provider="openai")
            schema_info = {'tables': {}}
            
            result = generate_sql(request, schema_info)
            
            assert result == "SELECT * FROM products"
            mock_anthropic_func.assert_called_once_with("Show all products", schema_info)
    
    @patch('core.llm_processor.generate_sql_with_openai')
    def test_generate_sql_request_preference_openai(self, mock_openai_func):
        # Test request preference when no keys available
        mock_openai_func.return_value = "SELECT * FROM orders"
        
        with patch.dict(os.environ, {}, clear=True):
            request = QueryRequest(query="Show all orders", llm_provider="openai")
            schema_info = {'tables': {}}
            
            result = generate_sql(request, schema_info)
            
            assert result == "SELECT * FROM orders"
            mock_openai_func.assert_called_once_with("Show all orders", schema_info)
    
    @patch('core.llm_processor.generate_sql_with_anthropic')
    def test_generate_sql_request_preference_anthropic(self, mock_anthropic_func):
        # Test request preference when no keys available
        mock_anthropic_func.return_value = "SELECT * FROM customers"
        
        with patch.dict(os.environ, {}, clear=True):
            request = QueryRequest(query="Show all customers", llm_provider="anthropic")
            schema_info = {'tables': {}}
            
            result = generate_sql(request, schema_info)
            
            assert result == "SELECT * FROM customers"
            mock_anthropic_func.assert_called_once_with("Show all customers", schema_info)
    
    @patch('core.llm_processor.generate_sql_with_openai')
    def test_generate_sql_both_keys_openai_priority(self, mock_openai_func):
        # Test that OpenAI has priority when both keys exist
        mock_openai_func.return_value = "SELECT * FROM inventory"
        
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'openai-key', 'ANTHROPIC_API_KEY': 'anthropic-key'}):
            request = QueryRequest(query="Show inventory", llm_provider="anthropic")
            schema_info = {'tables': {}}
            
            result = generate_sql(request, schema_info)
            
            assert result == "SELECT * FROM inventory"
            mock_openai_func.assert_called_once_with("Show inventory", schema_info)
    
    @patch('core.llm_processor.generate_sql_with_openai')
    def test_generate_sql_only_openai_key(self, mock_openai_func):
        # Test when only OpenAI key exists
        mock_openai_func.return_value = "SELECT * FROM sales"
        
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'openai-key'}, clear=True):
            request = QueryRequest(query="Show sales data", llm_provider="anthropic")
            schema_info = {'tables': {}}
            
            result = generate_sql(request, schema_info)
            
            assert result == "SELECT * FROM sales"
            mock_openai_func.assert_called_once_with("Show sales data", schema_info)


SAMPLE_SCHEMA = {"columns": {"id": "INTEGER", "name": "TEXT", "email": "TEXT", "age": "INTEGER"}}
SAMPLE_ROWS = [
    {"id": 1, "name": "Alice", "email": "alice@example.com", "age": 30},
    {"id": 2, "name": "Bob", "email": "bob@example.com", "age": 25},
]
GENERATED_ROWS = [
    {"id": 3, "name": "Carol", "email": "carol@example.com", "age": 28},
] * 10


class TestGenerateRandomData:

    @patch('core.llm_processor.OpenAI')
    def test_generate_random_data_with_openai_success(self, mock_openai_class):
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps(GENERATED_ROWS)
        mock_client.chat.completions.create.return_value = mock_response

        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            result = generate_random_data_with_openai("users", SAMPLE_SCHEMA, SAMPLE_ROWS)

        assert isinstance(result, list)
        assert len(result) == 10
        assert result[0]["name"] == "Carol"

    @patch('core.llm_processor.OpenAI')
    def test_generate_random_data_with_openai_strips_markdown(self, mock_openai_class):
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices[0].message.content = f"```json\n{json.dumps(GENERATED_ROWS)}\n```"
        mock_client.chat.completions.create.return_value = mock_response

        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            result = generate_random_data_with_openai("users", SAMPLE_SCHEMA, SAMPLE_ROWS)

        assert isinstance(result, list)
        assert len(result) == 10

    @patch('core.llm_processor.OpenAI')
    def test_generate_random_data_with_openai_temperature(self, mock_openai_class):
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps(GENERATED_ROWS)
        mock_client.chat.completions.create.return_value = mock_response

        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            generate_random_data_with_openai("users", SAMPLE_SCHEMA, SAMPLE_ROWS)

        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs['temperature'] == 0.8

    def test_generate_random_data_with_openai_no_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(Exception) as exc_info:
                generate_random_data_with_openai("users", SAMPLE_SCHEMA, SAMPLE_ROWS)
            assert "OPENAI_API_KEY environment variable not set" in str(exc_info.value)

    @patch('core.llm_processor.Anthropic')
    def test_generate_random_data_with_anthropic_success(self, mock_anthropic_class):
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content[0].text = json.dumps(GENERATED_ROWS)
        mock_client.messages.create.return_value = mock_response

        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}):
            result = generate_random_data_with_anthropic("users", SAMPLE_SCHEMA, SAMPLE_ROWS)

        assert isinstance(result, list)
        assert len(result) == 10

    @patch('core.llm_processor.Anthropic')
    def test_generate_random_data_with_anthropic_strips_markdown(self, mock_anthropic_class):
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content[0].text = f"```\n{json.dumps(GENERATED_ROWS)}\n```"
        mock_client.messages.create.return_value = mock_response

        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}):
            result = generate_random_data_with_anthropic("users", SAMPLE_SCHEMA, SAMPLE_ROWS)

        assert isinstance(result, list)
        assert len(result) == 10

    @patch('core.llm_processor.Anthropic')
    def test_generate_random_data_with_anthropic_temperature(self, mock_anthropic_class):
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content[0].text = json.dumps(GENERATED_ROWS)
        mock_client.messages.create.return_value = mock_response

        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}):
            generate_random_data_with_anthropic("users", SAMPLE_SCHEMA, SAMPLE_ROWS)

        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs['temperature'] == 0.8

    def test_generate_random_data_with_anthropic_no_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(Exception) as exc_info:
                generate_random_data_with_anthropic("users", SAMPLE_SCHEMA, SAMPLE_ROWS)
            assert "ANTHROPIC_API_KEY environment variable not set" in str(exc_info.value)

    @patch('core.llm_processor.generate_random_data_with_openai')
    def test_generate_random_data_routes_to_openai(self, mock_openai_func):
        mock_openai_func.return_value = GENERATED_ROWS

        with patch.dict(os.environ, {'OPENAI_API_KEY': 'key', 'ANTHROPIC_API_KEY': 'key2'}):
            result = generate_random_data("users", SAMPLE_SCHEMA, SAMPLE_ROWS)

        mock_openai_func.assert_called_once_with("users", SAMPLE_SCHEMA, SAMPLE_ROWS)
        assert result == GENERATED_ROWS

    @patch('core.llm_processor.generate_random_data_with_anthropic')
    def test_generate_random_data_routes_to_anthropic_fallback(self, mock_anthropic_func):
        mock_anthropic_func.return_value = GENERATED_ROWS

        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'key'}, clear=True):
            result = generate_random_data("users", SAMPLE_SCHEMA, SAMPLE_ROWS)

        mock_anthropic_func.assert_called_once_with("users", SAMPLE_SCHEMA, SAMPLE_ROWS)
        assert result == GENERATED_ROWS

    def test_generate_random_data_raises_when_no_keys(self):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                generate_random_data("users", SAMPLE_SCHEMA, SAMPLE_ROWS)
            assert "No LLM API key found" in str(exc_info.value)