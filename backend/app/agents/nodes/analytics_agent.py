"""Analytics visualization agent node for chart generation."""

import time
from typing import Any

from app.agents.state import NexusState
from app.services.chart_service import determine_chart_config, generate_chart_base64


async def analytics_node(state: NexusState) -> dict[str, Any]:
    """
    Analytics node: evaluates if database query results can be visualized,
    selects chart configuration, and generates Plotly base64 PNG.
    """
    start_time = time.time()
    
    # 1. Skip if SQL results are empty or not present
    results = state.get("sql_results")
    if not results or "error" in results[0] if results else False:
        trace = {
            "node_name": "AnalyticsAgent",
            "status": "skipped",
            "latency_ms": 0,
            "tokens_used": 0,
            "metadata": {"reason": "No SQL results available or error occurred."}
        }
        return {
            "chart_base64": None,
            "agent_trace": [trace]
        }
        
    query = state["original_query"]
    
    chart_base64 = None
    config = None
    status = "success"
    
    try:
        # 2. Determine chart configuration via GPT-4o
        config = await determine_chart_config(query, results)
        
        # 3. Generate chart image base64 if config is suitable
        if config:
            chart_base64 = generate_chart_base64(results, config)
            if not chart_base64:
                status = "failed"
        else:
            status = "skipped"  # Not suitable for chart
            
    except Exception as e:
        status = "failed"
        print(f"Analytics node execution error: {e}")
        
    latency = int((time.time() - start_time) * 1000)
    
    trace = {
        "node_name": "AnalyticsAgent",
        "status": status,
        "latency_ms": latency,
        "tokens_used": 0,
        "metadata": {
            "chart_config": config,
            "chart_generated": chart_base64 is not None
        }
    }
    
    return {
        "chart_base64": chart_base64,
        "agent_trace": [trace]
    }
