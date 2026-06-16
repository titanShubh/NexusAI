"""SQL Service for schema introspection, SQL generation, safety validation, and execution."""

import re
from decimal import Decimal
from typing import Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from openai import AsyncOpenAI

from app.config import get_settings

settings = get_settings()


async def get_db_schema(db: AsyncSession) -> str:
    """Dynamically introspect database tables, columns, types, and fetch sample data."""
    schema_info = []
    
    # Query for all user tables in public schema
    tables_query = text(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'public' AND table_name NOT IN ('users', 'documents', 'document_chunks', 'conversations', 'messages', 'query_logs');"
    )
    result = await db.execute(tables_query)
    tables = [row[0] for row in result.fetchall()]
    
    for table in tables:
        # Get column details
        cols_query = text(
            "SELECT column_name, data_type, is_nullable "
            "FROM information_schema.columns "
            "WHERE table_name = :table_name AND table_schema = 'public';"
        )
        cols_result = await db.execute(cols_query, {"table_name": table})
        columns = cols_result.fetchall()
        
        schema_info.append(f"Table: {table}")
        schema_info.append("Columns:")
        for col in columns:
            name, dtype, nullable = col
            null_str = "NULL" if nullable == "YES" else "NOT NULL"
            schema_info.append(f"  - {name} ({dtype}) {null_str}")
        
        # Get 3 sample rows
        sample_query = text(f"SELECT * FROM {table} LIMIT 3;")
        try:
            sample_result = await db.execute(sample_query)
            sample_rows = sample_result.fetchall()
            keys = sample_result.keys()
            if sample_rows:
                schema_info.append("Sample Rows:")
                for row in sample_rows:
                    row_dict = {keys[i]: str(row[i]) for i in range(len(keys))}
                    schema_info.append(f"  {row_dict}")
        except Exception as e:
            schema_info.append(f"  (Failed to fetch samples: {e})")
            
        schema_info.append("-" * 40)
        
    return "\n".join(schema_info)


async def generate_sql(query: str, schema_context: str) -> str:
    """Use GPT-4o to generate standard read-only PostgreSQL query based on natural language."""
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    
    system_prompt = (
        "You are an expert PostgreSQL SQL generator.\n"
        "Generate a valid PostgreSQL query to answer the user's question.\n"
        "You must output ONLY the raw SQL query. Do not wrap it in markdown block tags (e.g. do not use ```sql or ```) and do not provide any extra explanation.\n"
        "Only query tables described in the schema context below.\n"
        "Make sure to perform only read-only (SELECT) queries.\n\n"
        f"Database Schema:\n{schema_context}"
    )
    
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Query: {query}"}
        ],
        temperature=0.0
    )
    
    sql = response.choices[0].message.content or ""
    # Strip any markdown blocks if the model still generated them
    sql = re.sub(r"```(sql)?", "", sql).strip()
    return sql


def validate_sql(sql: str) -> tuple[bool, str]:
    """
    Validate SQL safety.
    Returns (is_safe, error_reason).
    Rejects DML statements (INSERT, UPDATE, DELETE, DROP, etc.) and potential injection patterns.
    """
    sql_clean = sql.strip().upper()
    
    # 1. Must start with SELECT or WITH
    if not (sql_clean.startswith("SELECT") or sql_clean.startswith("WITH")):
        return False, "Query must start with SELECT or WITH."
        
    # 2. Block destructive words/DML
    blocked_keywords = [
        "INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE", "ALTER", "CREATE", 
        "REPLACE", "GRANT", "REVOKE", "MERGE", "EXEC", "EXECUTE", "UPSERT"
    ]
    
    # Check word boundary matching
    for keyword in blocked_keywords:
        pattern = r"\b" + re.escape(keyword) + r"\b"
        if re.search(pattern, sql_clean):
            return False, f"Unauthorized SQL keyword detected: {keyword}"
            
    # 3. Block multiple statements (semicolon injection)
    # Allow a single trailing semicolon but reject semicolons in between statements
    semicolon_splits = [s.strip() for s in sql.split(";") if s.strip()]
    if len(semicolon_splits) > 1:
        return False, "Multiple SQL statements are not allowed."
        
    return True, ""


async def execute_sql(sql: str, db: AsyncSession) -> list[dict[str, Any]]:
    """Execute SQL query safely and return results formatted for JSON serialization."""
    # Validate safety
    is_safe, error_reason = validate_sql(sql)
    if not is_safe:
        raise ValueError(f"SQL Validation Error: {error_reason}")
        
    # Execute query
    result = await db.execute(text(sql))
    rows = result.fetchall()
    keys = result.keys()
    
    formatted_results = []
    for row in rows:
        row_dict = {}
        for i, val in enumerate(row):
            key = keys[i]
            # Handle non-serializable decimal/datetime types
            if isinstance(val, Decimal):
                row_dict[key] = float(val)
            elif hasattr(val, "isoformat"):  # date, datetime
                row_dict[key] = val.isoformat()
            else:
                row_dict[key] = val
        formatted_results.append(row_dict)
        
    return formatted_results
