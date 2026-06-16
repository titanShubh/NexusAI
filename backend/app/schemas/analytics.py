from datetime import datetime
from typing import Any, Optional
from uuid import UUID
from pydantic import BaseModel


class QueryMetrics(BaseModel):
    total_queries: int
    avg_latency_ms: float
    total_tokens_used: int
    agent_distribution: dict[str, int]  # counts of agent activations (rag, sql, hybrid, analytics)
    confidence_histogram: dict[str, int]  # counts of queries falling into ranges (e.g. "0.0-0.2", "0.2-0.4", etc.)


class AgentTrace(BaseModel):
    node_name: str
    status: str  # success, failed, skipped
    latency_ms: int
    tokens_used: int
    metadata: Optional[dict[str, Any]] = None


class EvalScores(BaseModel):
    faithfulness: float
    relevance: float
    sql_safety: float
    confidence_score: float
