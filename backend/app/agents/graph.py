"""LangGraph compilation and orchestration assembly for NexusAI."""

from typing import Union
from langgraph.graph import StateGraph, START, END

from app.agents.state import NexusState
from app.agents.nodes import (
    guardrails_node,
    supervisor_node,
    rag_node,
    sql_node,
    analytics_node,
    eval_node,
    response_node,
)


def route_from_supervisor(state: NexusState) -> Union[str, list[str]]:
    """
    Conditional routing function based on the supervisor's route decision.
    Spawns parallel execution branches when 'hybrid' route is chosen.
    """
    decision = state.get("route_decision")
    
    if decision == "rag":
        return "rag"
    elif decision == "sql":
        return "sql"
    elif decision == "analytics":
        return "sql"  # Analytics requires SQL results first, which then transitions to analytics
    elif decision == "hybrid":
        return ["rag", "sql"]  # Executes RAG and SQL nodes in parallel
    else:
        # direct or fallback
        return "eval"


# Assemble the state workflow graph
workflow = StateGraph(NexusState)

# Add all agent nodes
workflow.add_node("guardrails", guardrails_node)
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("rag", rag_node)
workflow.add_node("sql", sql_node)
workflow.add_node("analytics", analytics_node)
workflow.add_node("eval", eval_node)
workflow.add_node("response", response_node)

# Define edge flow
workflow.add_edge(START, "guardrails")
workflow.add_edge("guardrails", "supervisor")

# Routing conditional transitions
workflow.add_conditional_edges(
    "supervisor",
    route_from_supervisor,
    {
        "rag": "rag",
        "sql": "sql",
        "eval": "eval"
    }
)

def route_from_rag(state: NexusState) -> str:
    """
    Conditional routing function for the RAG node.
    If the user wants a chart/graph, route to the analytics node.
    Otherwise, go directly to the evaluation node.
    """
    query_lower = state["original_query"].lower()
    has_chart_intent = any(w in query_lower for w in ("plot", "chart", "graph", "visualize", "histogram"))
    if has_chart_intent:
        return "analytics"
    return "eval"


# Branch transitions merging at the eval node
workflow.add_conditional_edges(
    "rag",
    route_from_rag,
    {
        "analytics": "analytics",
        "eval": "eval"
    }
)
workflow.add_edge("sql", "analytics")
workflow.add_edge("analytics", "eval")

# Final response transitions
workflow.add_edge("eval", "response")
workflow.add_edge("response", END)

# Compile graph
compiled_graph = workflow.compile()
