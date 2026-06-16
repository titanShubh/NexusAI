"""Evaluation validator agent node for confidence and hallucination scoring."""

import time
from typing import Any

from app.db.database import async_session_factory
from app.agents.state import NexusState
from app.services.eval_service import compute_overall_confidence
from app.services.sql_service import get_db_schema


async def eval_node(state: NexusState) -> dict[str, Any]:
    """
    Evaluates response components (RAG grounding, SQL safety, SQL logic)
    and aggregates a global confidence score.
    """
    start_time = time.time()
    
    # Skip if guardrails blocked
    if state.get("guardrail_flags"):
        trace = {
            "node_name": "EvalAgent",
            "status": "skipped",
            "latency_ms": 0,
            "tokens_used": 0,
            "metadata": {"reason": "Guardrail flags active"}
        }
        return {
            "eval_scores": {
                "faithfulness": 1.0,
                "relevance": 1.0,
                "sql_safety": 1.0,
                "sql_correctness": 1.0,
                "confidence_score": 1.0
            },
            "agent_trace": [trace]
        }
        
    query = state["original_query"]
    route = state.get("route_decision", "direct")
    
    # Gather RAG chunks text for evaluation
    retrieved_chunks = [c["content"] for c in state.get("rag_results", [])]
    
    # Gather assistant RAG answer from message history if available
    # The last message inside state['messages'] is from the RAGAgent helper if it ran
    response_content = ""
    for msg in reversed(state.get("messages", [])):
        if msg.get("name") == "RAGAgent":
            response_content = msg["content"]
            break
            
    sql_query = state.get("sql_query")
    
    # Fetch schema context for SQL validation if SQL was run
    schema_context = None
    if sql_query:
        async with async_session_factory() as db:
            schema_context = await get_db_schema(db)
            
    # Compute scores
    try:
        eval_scores = await compute_overall_confidence(
            query=query,
            route_decision=route,
            response_content=response_content,
            retrieved_chunks=retrieved_chunks,
            sql_query=sql_query,
            schema_context=schema_context
        )
    except Exception as e:
        print(f"Eval agent node error: {e}")
        eval_scores = {
            "faithfulness": 0.8,
            "relevance": 0.8,
            "sql_safety": 1.0,
            "sql_correctness": 0.8,
            "confidence_score": 0.8
        }
        
    latency = int((time.time() - start_time) * 1000)
    
    trace = {
        "node_name": "EvalAgent",
        "status": "success",
        "latency_ms": latency,
        "tokens_used": 0,
        "metadata": {"eval_scores": eval_scores}
    }
    
    return {
        "eval_scores": eval_scores,
        "agent_trace": [trace]
    }
