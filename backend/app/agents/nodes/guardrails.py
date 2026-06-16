"""Guardrails agent node for input query validation."""

import json
import time
from typing import Any
from openai import AsyncOpenAI

from app.config import get_settings
from app.agents.state import NexusState
from app.agents.prompts.system_prompts import GUARDRAILS_SYSTEM_PROMPT

settings = get_settings()


async def guardrails_node(state: NexusState) -> dict[str, Any]:
    """
    Validates user query input for prompt injection, SQL injection, PII, and malicious intent.
    """
    start_time = time.time()
    query = state["original_query"]
    
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    violations = []
    tokens = 0
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": GUARDRAILS_SYSTEM_PROMPT},
                {"role": "user", "content": f"Query to evaluate: {query}"}
            ],
            temperature=0.0
        )
        content = (response.choices[0].message.content or "").strip()
        tokens = response.usage.total_tokens if response.usage else 0
        
        # Clean markdown code block wraps
        if content.startswith("```"):
            content = content.replace("```json", "").replace("```", "").strip()
            
        violations = json.loads(content)
    except Exception as e:
        print(f"Guardrails node error: {e}")
        # Default to safe if LLM fails, or flag system error
        violations = []

    latency = int((time.time() - start_time) * 1000)
    
    trace = {
        "node_name": "Guardrails",
        "status": "success" if not violations else "flagged",
        "latency_ms": latency,
        "tokens_used": tokens,
        "metadata": {"violations": violations}
    }
    
    return {
        "guardrail_flags": violations,
        "agent_trace": [trace]
    }
