import os
from typing import Dict, Any, Optional
from openai import OpenAI
from anthropic import Anthropic
from core.data_models import QueryRequest


def _build_previous_turn_block(previous_query: Optional[str], previous_sql: Optional[str]) -> str:
    """Return the conversational-context preamble, or empty string if context is not active."""
    if not previous_query or not previous_sql:
        return ""
    return (
        "Previous turn (use as conversational context for the new question):\n"
        f"- Previous question: \"{previous_query}\"\n"
        f"- Previous SQL: {previous_sql}\n"
        "\n"
        "When the new question references the previous result with words like \"that\", \"those\", \"it\", \"now filter...\", \"now group by...\", \"show that as...\", interpret it as a refinement of the previous SQL. Do not re-explain or repeat the previous SQL; produce a single new SQL statement that satisfies the new question.\n"
        "\n"
    )


def generate_sql_with_openai(
    query_text: str,
    schema_info: Dict[str, Any],
    previous_query: Optional[str] = None,
    previous_sql: Optional[str] = None,
) -> str:
    """
    Generate SQL query using OpenAI API
    """
    try:
        # Get API key from environment
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        client = OpenAI(api_key=api_key)

        # Format schema for prompt
        schema_description = format_schema_for_prompt(schema_info)
        previous_turn_block = _build_previous_turn_block(previous_query, previous_sql)

        # Create prompt
        prompt = f"""Given the following database schema:

{schema_description}

{previous_turn_block}Convert this natural language query to SQL: "{query_text}"

Rules:
- Return ONLY the SQL query, no explanations
- Use proper SQLite syntax
- Handle date/time queries appropriately (e.g., "last week" = date('now', '-7 days'))
- Be careful with column names and table names
- If the query is ambiguous, make reasonable assumptions
- For multi-table queries, use proper JOIN conditions to avoid Cartesian products
- Limit results to reasonable amounts (e.g., add LIMIT 100 for large result sets)
- When joining tables, use meaningful relationships between tables
- NEVER include SQL comments (-- or /* */) in the query

SQL Query:"""
        
        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4.1-2025-04-14",
            messages=[
                {"role": "system", "content": "You are a SQL expert. Convert natural language to SQL queries."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=500
        )
        
        sql = response.choices[0].message.content.strip()
        
        # Clean up the SQL (remove markdown if present)
        if sql.startswith("```sql"):
            sql = sql[6:]
        if sql.startswith("```"):
            sql = sql[3:]
        if sql.endswith("```"):
            sql = sql[:-3]
        
        return sql.strip()
        
    except Exception as e:
        raise Exception(f"Error generating SQL with OpenAI: {str(e)}")

def generate_sql_with_anthropic(
    query_text: str,
    schema_info: Dict[str, Any],
    previous_query: Optional[str] = None,
    previous_sql: Optional[str] = None,
) -> str:
    """
    Generate SQL query using Anthropic API
    """
    try:
        # Get API key from environment
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")

        client = Anthropic(api_key=api_key)

        # Format schema for prompt
        schema_description = format_schema_for_prompt(schema_info)
        previous_turn_block = _build_previous_turn_block(previous_query, previous_sql)

        # Create prompt
        prompt = f"""Given the following database schema:

{schema_description}

{previous_turn_block}Convert this natural language query to SQL: "{query_text}"

Rules:
- Return ONLY the SQL query, no explanations
- Use proper SQLite syntax
- Handle date/time queries appropriately (e.g., "last week" = date('now', '-7 days'))
- Be careful with column names and table names
- If the query is ambiguous, make reasonable assumptions
- For multi-table queries, use proper JOIN conditions to avoid Cartesian products
- Limit results to reasonable amounts (e.g., add LIMIT 100 for large result sets)
- When joining tables, use meaningful relationships between tables
- NEVER include SQL comments (-- or /* */) in the query

SQL Query:"""
        
        # Call Anthropic API
        response = client.messages.create(
            model="claude-sonnet-4-0",
            max_tokens=500,
            temperature=0.1,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        sql = response.content[0].text.strip()
        
        # Clean up the SQL (remove markdown if present)
        if sql.startswith("```sql"):
            sql = sql[6:]
        if sql.startswith("```"):
            sql = sql[3:]
        if sql.endswith("```"):
            sql = sql[:-3]
        
        return sql.strip()
        
    except Exception as e:
        raise Exception(f"Error generating SQL with Anthropic: {str(e)}")

def format_schema_for_prompt(schema_info: Dict[str, Any]) -> str:
    """
    Format database schema for LLM prompt
    """
    lines = []
    
    for table_name, table_info in schema_info.get('tables', {}).items():
        lines.append(f"Table: {table_name}")
        lines.append("Columns:")
        
        for col_name, col_type in table_info['columns'].items():
            lines.append(f"  - {col_name} ({col_type})")
        
        lines.append(f"Row count: {table_info['row_count']}")
        lines.append("")
    
    return "\n".join(lines)

def generate_random_query_with_openai(schema_info: Dict[str, Any]) -> str:
    """
    Generate a random natural language query using OpenAI API
    """
    try:
        # Get API key from environment
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        client = OpenAI(api_key=api_key)
        
        # Format schema for prompt
        schema_description = format_schema_for_prompt(schema_info)
        
        # Create prompt
        prompt = f"""Given the following database schema:

{schema_description}

Generate an interesting natural language query that someone might ask about this data. 
The query should be:
- Contextually relevant to the table structures and columns
- Natural and conversational
- Maximum two sentences
- Something that would demonstrate the capability of natural language to SQL conversion
- Varied in complexity (sometimes simple, sometimes complex with JOINs or aggregations)
- Do NOT include any SQL syntax, comments, or special characters

Examples of good queries:
- "What are the top 5 products by revenue?"
- "Show me all customers who ordered in the last month."
- "Which employees have the highest average sales? List their names and departments."

Natural language query:"""
        
        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4.1-2025-04-14",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates interesting questions about data."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=100
        )
        
        query = response.choices[0].message.content.strip()
        return query
        
    except Exception as e:
        raise Exception(f"Error generating random query with OpenAI: {str(e)}")

def generate_random_query_with_anthropic(schema_info: Dict[str, Any]) -> str:
    """
    Generate a random natural language query using Anthropic API
    """
    try:
        # Get API key from environment
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        
        client = Anthropic(api_key=api_key)
        
        # Format schema for prompt
        schema_description = format_schema_for_prompt(schema_info)
        
        # Create prompt
        prompt = f"""Given the following database schema:

{schema_description}

Generate an interesting natural language query that someone might ask about this data. 
The query should be:
- Contextually relevant to the table structures and columns
- Natural and conversational
- Maximum two sentences
- Something that would demonstrate the capability of natural language to SQL conversion
- Varied in complexity (sometimes simple, sometimes complex with JOINs or aggregations)
- Do NOT include any SQL syntax, comments, or special characters

Examples of good queries:
- "What are the top 5 products by revenue?"
- "Show me all customers who ordered in the last month."
- "Which employees have the highest average sales? List their names and departments."

Natural language query:"""
        
        # Call Anthropic API
        response = client.messages.create(
            model="claude-sonnet-4-0",
            max_tokens=100,
            temperature=0.8,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        query = response.content[0].text.strip()
        return query
        
    except Exception as e:
        raise Exception(f"Error generating random query with Anthropic: {str(e)}")

def generate_random_query(schema_info: Dict[str, Any]) -> str:
    """
    Route to appropriate LLM provider for random query generation
    Priority: 1) OpenAI API key exists, 2) Anthropic API key exists
    """
    openai_key = os.environ.get("OPENAI_API_KEY")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    
    # Check API key availability (OpenAI priority)
    if openai_key:
        return generate_random_query_with_openai(schema_info)
    elif anthropic_key:
        return generate_random_query_with_anthropic(schema_info)
    else:
        raise ValueError("No LLM API key found. Please set either OPENAI_API_KEY or ANTHROPIC_API_KEY")

def generate_sql(request: QueryRequest, schema_info: Dict[str, Any]) -> str:
    """
    Route to appropriate LLM provider based on API key availability and request preference.
    Priority: 1) OpenAI API key exists, 2) Anthropic API key exists, 3) request.llm_provider
    """
    openai_key = os.environ.get("OPENAI_API_KEY")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")

    # Check API key availability first (OpenAI priority)
    if openai_key:
        return generate_sql_with_openai(
            request.query,
            schema_info,
            previous_query=request.previous_query,
            previous_sql=request.previous_sql,
        )
    elif anthropic_key:
        return generate_sql_with_anthropic(
            request.query,
            schema_info,
            previous_query=request.previous_query,
            previous_sql=request.previous_sql,
        )

    # Fall back to request preference if both keys available or neither available
    if request.llm_provider == "openai":
        return generate_sql_with_openai(
            request.query,
            schema_info,
            previous_query=request.previous_query,
            previous_sql=request.previous_sql,
        )
    else:
        return generate_sql_with_anthropic(
            request.query,
            schema_info,
            previous_query=request.previous_query,
            previous_sql=request.previous_sql,
        )