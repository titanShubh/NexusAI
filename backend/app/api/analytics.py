"""Observability and analytics API routes."""

from collections import Counter
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.dependencies import get_db, get_current_user
from app.db.models import User, Message, QueryLog
from app.schemas.analytics import QueryMetrics

router = APIRouter(tags=["Analytics"])


@router.get("/dashboard", response_model=QueryMetrics)
async def get_dashboard_metrics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Computes system-level observability metrics from query logs and messages.
    """
    # 1. Total Queries count for user's conversations
    # Filter logs belonging to current user
    logs_query = (
        select(QueryLog)
        .join(QueryLog.conversation)
        .where(QueryLog.conversation.has(user_id=current_user.id))
    )
    result = await db.execute(logs_query)
    logs = result.scalars().all()
    
    total_queries = len(logs)
    
    if total_queries == 0:
        return QueryMetrics(
            total_queries=0,
            avg_latency_ms=0.0,
            total_tokens_used=0,
            agent_distribution={"rag": 0, "sql": 0, "hybrid": 0, "direct": 0},
            confidence_histogram={"0.0-0.2": 0, "0.2-0.4": 0, "0.4-0.6": 0, "0.6-0.8": 0, "0.8-1.0": 0}
        )
        
    # 2. Avg Latency
    avg_latency = sum(log.total_latency_ms or 0 for log in logs) / total_queries
    
    # 3. Agent Route Distribution
    routes = [log.route_decision for log in logs]
    agent_distribution = Counter(routes)
    # Ensure all routes have at least a 0 count
    for r in ("rag", "sql", "hybrid", "direct"):
        if r not in agent_distribution:
            agent_distribution[r] = 0

    # 4. Total Tokens used
    tokens_query = (
        select(func.sum(Message.tokens_used))
        .join(Message.conversation)
        .where(Message.conversation.has(user_id=current_user.id), Message.role == "assistant")
    )
    tokens_result = await db.execute(tokens_query)
    total_tokens = tokens_result.scalar() or 0
    
    # 5. Confidence Score Histogram
    confidence_histogram = {
        "0.0-0.2": 0,
        "0.2-0.4": 0,
        "0.4-0.6": 0,
        "0.6-0.8": 0,
        "0.8-1.0": 0
    }
    
    for log in logs:
        scores = log.eval_scores or {}
        confidence = scores.get("confidence_score", 1.0)
        
        if confidence <= 0.2:
            confidence_histogram["0.0-0.2"] += 1
        elif confidence <= 0.4:
            confidence_histogram["0.2-0.4"] += 1
        elif confidence <= 0.6:
            confidence_histogram["0.4-0.6"] += 1
        elif confidence <= 0.8:
            confidence_histogram["0.6-0.8"] += 1
        else:
            confidence_histogram["0.8-1.0"] += 1
            
    return QueryMetrics(
        total_queries=total_queries,
        avg_latency_ms=round(avg_latency, 2),
        total_tokens_used=total_tokens,
        agent_distribution=dict(agent_distribution),
        confidence_histogram=confidence_histogram
    )


@router.get("/traces/{conversation_id}")
async def get_conversation_traces(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed execution trace files and logs for a single conversation.
    """
    # Verify ownership
    logs_query = (
        select(QueryLog)
        .join(QueryLog.conversation)
        .where(QueryLog.conversation_id == conversation_id, QueryLog.conversation.has(user_id=current_user.id))
        .order_by(QueryLog.created_at.asc())
    )
    result = await db.execute(logs_query)
    logs = result.scalars().all()
    
    messages_query = (
        select(Message)
        .where(Message.conversation_id == conversation_id, Message.role == "assistant")
        .order_by(Message.created_at.asc())
    )
    msg_result = await db.execute(messages_query)
    messages = msg_result.scalars().all()
    
    traces = []
    # Match messages and query logs by timestamp / index sequence
    for log in logs:
        traces.append({
            "query_log_id": log.id,
            "original_query": log.original_query,
            "route_decision": log.route_decision,
            "decomposed_queries": log.decomposed_queries,
            "eval_scores": log.eval_scores,
            "latency_ms": log.total_latency_ms,
            "timestamp": log.created_at.isoformat()
        })
        
    return {
        "conversation_id": conversation_id,
        "traces": traces,
        "assistant_messages": [
            {
                "id": m.id,
                "sql_query": m.sql_query,
                "chart_generated": m.chart_url is not None,
                "latency_ms": m.latency_ms,
                "tokens_used": m.tokens_used,
                "timestamp": m.created_at.isoformat()
            } for m in messages
        ]
    }
