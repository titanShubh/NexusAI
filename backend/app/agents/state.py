"""LangGraph state definition for the NexusAI multi-agent orchestrator."""

from typing import Annotated, Any, Optional, TypedDict
from uuid import UUID


def append_reducer(left: list, right: list) -> list:
    """Helper reducer to append list items instead of overwriting."""
    return left + right


class NexusState(TypedDict):
    """
    Key state variables tracked throughout the LangGraph agent pipeline.
    """
    # Conversational state
    messages: Annotated[list[dict[str, Any]], append_reducer]
    conversation_id: UUID
    user_id: UUID
    
    # Input query state
    original_query: str
    decomposed_queries: Optional[list[str]]
    
    # Routing & execution state
    route_decision: Optional[str]  # "rag" | "sql" | "hybrid" | "analytics" | "direct"
    guardrail_flags: list[str]
    
    # RAG results
    rag_results: list[dict[str, Any]]
    
    # SQL results
    sql_query: Optional[str]
    sql_results: list[dict[str, Any]]
    
    # Visualization
    chart_base64: Optional[str]
    
    # Evaluation & final response
    eval_scores: dict[str, Any]
    final_response: Optional[str]
    
    # Observability tracing
    agent_trace: Annotated[list[dict[str, Any]], append_reducer]
