"""Database Schema details endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.dependencies import get_db, get_current_user
from app.db.models import User

router = APIRouter(tags=["Database Schema"])


@router.get("/tables")
async def list_schema_tables(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns lists of available database tables, column details, and data types
    used in the demo business data catalog.
    """
    tables_query = text(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'public' AND table_name NOT IN ('users', 'documents', 'document_chunks', 'conversations', 'messages', 'query_logs');"
    )
    result = await db.execute(tables_query)
    tables = [row[0] for row in result.fetchall()]
    
    schema_details = {}
    for table in tables:
        cols_query = text(
            "SELECT column_name, data_type, is_nullable "
            "FROM information_schema.columns "
            "WHERE table_name = :table_name AND table_schema = 'public' "
            "ORDER BY ordinal_position;"
        )
        cols_result = await db.execute(cols_query, {"table_name": table})
        columns = cols_result.fetchall()
        
        schema_details[table] = [
            {
                "name": col[0],
                "type": col[1],
                "nullable": col[2] == "YES"
            } for col in columns
        ]
        
    return {"tables": schema_details}
