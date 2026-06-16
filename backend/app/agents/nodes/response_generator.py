"""Response generator agent node to compile the final unified markdown response."""

import json
import time
from typing import Any
from openai import AsyncOpenAI

from app.config import get_settings
from app.agents.state import NexusState
from app.agents.prompts.system_prompts import RESPONSE_GENERATOR_SYSTEM_PROMPT

settings = get_settings()


async def response_node(state: NexusState) -> dict[str, Any]:
    """
    Response node: synthesizes RAG + SQL + Chart results into a single
    markdown response for the user.
    """
    start_time = time.time()
    
    # 1. Handle Guardrail violations immediately
    if state.get("guardrail_flags"):
        reasons = ", ".join(state["guardrail_flags"])
        blocked_msg = f"⚠️ **Security Alert:** Your query was blocked by safety guardrails. Reasons: {reasons}."
        trace = {
            "node_name": "ResponseGen",
            "status": "success",
            "latency_ms": 0,
            "tokens_used": 0,
            "metadata": {"blocked": True}
        }
        return {
            "final_response": blocked_msg,
            "agent_trace": [trace]
        }
        
    query = state["original_query"]
    route = state.get("route_decision", "direct")
    eval_scores = state.get("eval_scores", {})
    confidence_score = eval_scores.get("confidence_score", 1.0)
    
    # 2. Extract RAG answer text from messages
    rag_content = ""
    for msg in reversed(state.get("messages", [])):
        if msg.get("name") == "RAGAgent":
            rag_content = msg["content"]
            break
            
    sql_query = state.get("sql_query")
    sql_results = state.get("sql_results", [])
    has_chart = state.get("chart_base64") is not None
    
    # 3. Create instruction block for compiler
    compiler_input = {
        "original_query": query,
        "route_decision": route,
        "confidence_score": confidence_score,
        "rag_agent_response": rag_content if route in ("rag", "hybrid") else "N/A",
        "sql_query": sql_query if route in ("sql", "hybrid", "analytics") else "N/A",
        "sql_results": sql_results[:50] if (route in ("sql", "hybrid", "analytics") or has_chart) else [],  # limit rows passed to compiler
        "has_chart_visualization": has_chart
    }
    
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    tokens = 0
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": RESPONSE_GENERATOR_SYSTEM_PROMPT},
                {"role": "user", "content": f"Inputs for Compilation:\n{json.dumps(compiler_input)}"}
            ],
            temperature=0.2
        )
        final_answer = response.choices[0].message.content or ""
        tokens = response.usage.total_tokens if response.usage else 0
    except Exception as e:
        print(f"Response compilation error: {e}")
        # Manual fallback synthesis
        final_answer = ""
        if route in ("rag", "hybrid") and rag_content:
            final_answer += f"{rag_content}\n\n"
        if route in ("sql", "hybrid", "analytics") and sql_results:
            final_answer += f"**SQL Result Data:**\n```json\n{json.dumps(sql_results[:10], indent=2)}\n```\n"
            if not final_answer:
                final_answer = "No data returned."

    latency = int((time.time() - start_time) * 1000)
    
    trace = {
        "node_name": "ResponseGen",
        "status": "success",
        "latency_ms": latency,
        "tokens_used": tokens,
        "metadata": {"route": route, "confidence": confidence_score}
    }
    
    return {
        "final_response": final_answer,
        "agent_trace": [trace]
    }
