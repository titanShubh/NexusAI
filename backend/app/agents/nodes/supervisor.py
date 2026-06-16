"""Supervisor routing agent node for query analysis and decomposition."""

import json
import time
from typing import Any
from sqlalchemy import select
from openai import AsyncOpenAI

from app.config import get_settings
from app.db.database import async_session_factory
from app.db.models import Document
from app.agents.state import NexusState
from app.agents.prompts.system_prompts import SUPERVISOR_SYSTEM_PROMPT
from app.services.sql_service import get_db_schema

settings = get_settings()


async def supervisor_node(state: NexusState) -> dict[str, Any]:
    """
    Analyzes query intent, decides routing (rag, sql, hybrid, direct) and decomposes query.
    """
    start_time = time.time()
    query = state["original_query"]
    user_id = state["user_id"]
    
    # Check if guardrails blocked
    if state.get("guardrail_flags"):
        trace = {
            "node_name": "Supervisor",
            "status": "skipped",
            "latency_ms": 0,
            "tokens_used": 0,
            "metadata": {"reason": "Guardrail flags active"}
        }
        return {
            "route_decision": "direct",
            "decomposed_queries": [],
            "agent_trace": [trace]
        }
        
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    route = "direct"
    decomposed = [query]
    tokens = 0
    
    async with async_session_factory() as db:
        # 1. Fetch available documents
        result = await db.execute(
            select(Document.filename)
            .where(Document.user_id == user_id, Document.upload_status == "completed")
        )
        filenames = [row[0] for row in result.fetchall()]
        doc_list_str = "\n".join([f"- {f}" for f in filenames]) if filenames else "No documents uploaded."
        
        # 2. Fetch schema context
        schema_context = await get_db_schema(db)
        
    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": SUPERVISOR_SYSTEM_PROMPT.format(
                        document_list=doc_list_str,
                        schema_context=schema_context
                    )
                },
                {"role": "user", "content": f"Query to route: {query}"}
            ],
            temperature=0.0
        )
        content = (response.choices[0].message.content or "").strip()
        tokens = response.usage.total_tokens if response.usage else 0
        
        if content.startswith("```"):
            content = content.replace("```json", "").replace("```", "").strip()
            
        data = json.loads(content)
        route = data.get("route", "direct")
        decomposed = data.get("decomposed_queries", [query])
    except Exception as e:
        print(f"Supervisor routing error: {e}")
        # Default fallback
        route = "direct"
        decomposed = [query]

    latency = int((time.time() - start_time) * 1000)
    
    trace = {
        "node_name": "Supervisor",
        "status": "success",
        "latency_ms": latency,
        "tokens_used": tokens,
        "metadata": {
            "route_decision": route,
            "decomposed_queries": decomposed
        }
    }
    
    return {
        "route_decision": route,
        "decomposed_queries": decomposed,
        "agent_trace": [trace]
    }
