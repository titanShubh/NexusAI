"""SQL execution agent node for database querying."""

import time
from typing import Any

from app.db.database import async_session_factory
from app.agents.state import NexusState
from app.services.sql_service import get_db_schema, generate_sql, validate_sql, execute_sql


async def sql_node(state: NexusState) -> dict[str, Any]:
    """
    SQL node: gets schema context, generates SQL via GPT-4o, validates, and runs the query.
    """
    start_time = time.time()
    
    # 1. Skip if SQL is not required
    route = state.get("route_decision")
    if route not in ("sql", "hybrid", "analytics"):
        trace = {
            "node_name": "SQLAgent",
            "status": "skipped",
            "latency_ms": 0,
            "tokens_used": 0,
            "metadata": {"reason": f"Route '{route}' does not require SQL."}
        }
        return {
            "sql_query": None,
            "sql_results": [],
            "agent_trace": [trace]
        }
        
    query = state["original_query"]
    
    sql = None
    results = []
    error_msg = None
    status = "success"
    
    async with async_session_factory() as db:
        try:
            # 2. Get database schema context
            schema_context = await get_db_schema(db, query)
            
            # 3. Generate SQL from user query
            sql = await generate_sql(query, schema_context)
            
            if not sql:
                raise ValueError("No SQL query could be generated.")
                
            # 4. Validate SQL query safety
            is_safe, reason = validate_sql(sql)
            if not is_safe:
                status = "failed"
                error_msg = f"SQL Blocked by Guardrails: {reason}"
                results = [{"error": error_msg}]
            else:
                # 5. Execute SQL query
                results = await execute_sql(sql, db)
                
        except Exception as e:
            status = "failed"
            error_msg = str(e)
            results = [{"error": f"SQL Execution Error: {error_msg}"}]
            print(f"SQL node execution error: {e}")
            
    latency = int((time.time() - start_time) * 1000)
    
    trace = {
        "node_name": "SQLAgent",
        "status": status,
        "latency_ms": latency,
        "tokens_used": 0,  # tokens counted in service layer if needed
        "metadata": {
            "generated_sql": sql,
            "error": error_msg,
            "rows_returned": len(results) if status == "success" else 0
        }
    }
    
    return {
        "sql_query": sql,
        "sql_results": results,
        "agent_trace": [trace]
    }
