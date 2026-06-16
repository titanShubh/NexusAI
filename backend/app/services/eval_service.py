"""Evaluation and confidence scoring service using GPT-4o as a judge."""

import json
from typing import Any, Optional
from openai import AsyncOpenAI

from app.config import get_settings
from app.services.sql_service import validate_sql

settings = get_settings()


async def evaluate_faithfulness(answer: str, chunks: list[str]) -> float:
    """Evaluate if the generated response is strictly grounded in the retrieved document chunks."""
    if not chunks or not answer:
        return 1.0  # Default to 1.0 if no documents were retrieved/answered
        
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    
    context_text = "\n\n".join([f"--- Chunk {i+1} ---\n{chunk}" for i, chunk in enumerate(chunks)])
    
    system_prompt = (
        "You are an AI evaluator checking for Hallucinations.\n"
        "Analyze the provided context chunks and the generated answer.\n"
        "Determine what percentage of facts in the generated answer are directly supported by the context.\n"
        "Your response MUST be a JSON object with a single key 'faithfulness_score', a float between 0.0 (completely hallucinated/unsupported) and 1.0 (perfectly faithful/supported).\n"
        "Do not include any explanation or markdown code block wraps."
    )
    
    user_content = (
        f"Context Chunks:\n{context_text}\n\n"
        f"Generated Answer:\n{answer}"
    )
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            temperature=0.0
        )
        content = (response.choices[0].message.content or "").strip()
        if content.startswith("```"):
            content = content.replace("```json", "").replace("```", "").strip()
            
        data = json.loads(content)
        return float(data.get("faithfulness_score", 1.0))
    except Exception as e:
        print(f"Failed to evaluate faithfulness: {e}")
        return 0.8  # Fallback score on API errors


async def evaluate_retrieval_relevance(query: str, chunks: list[str]) -> float:
    """Evaluate how relevant the retrieved document chunks are to the user's original query."""
    if not chunks:
        return 0.0
        
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    
    context_text = "\n\n".join([f"--- Chunk {i+1} ---\n{chunk}" for i, chunk in enumerate(chunks)])
    
    system_prompt = (
        "You are an AI evaluator checking Retrieval Relevance.\n"
        "Analyze the user query and the retrieved context chunks.\n"
        "Evaluate what proportion of the retrieved chunks contain information relevant to answering the query.\n"
        "Your response MUST be a JSON object with a single key 'relevance_score', a float between 0.0 (no relevant info retrieved) and 1.0 (all chunks highly relevant).\n"
        "Do not include any explanation or markdown code block wraps."
    )
    
    user_content = (
        f"User Query: {query}\n\n"
        f"Retrieved Chunks:\n{context_text}"
    )
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            temperature=0.0
        )
        content = (response.choices[0].message.content or "").strip()
        if content.startswith("```"):
            content = content.replace("```json", "").replace("```", "").strip()
            
        data = json.loads(content)
        return float(data.get("relevance_score", 1.0))
    except Exception as e:
        print(f"Failed to evaluate relevance: {e}")
        return 0.8  # Fallback score


def evaluate_sql_safety(sql: str) -> float:
    """Run static SQL safety check. Returns 1.0 if safe, 0.0 if blocked."""
    is_safe, _ = validate_sql(sql)
    return 1.0 if is_safe else 0.0


async def evaluate_sql_correctness(query: str, sql: str, schema_context: str) -> float:
    """Evaluate if the generated SQL query is logically correct for answering the user's business query."""
    if not sql:
        return 0.0
        
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    
    system_prompt = (
        "You are an expert SQL auditor.\n"
        "Review the generated SQL query against the database schema and the user's query.\n"
        "Determine if the SQL query will accurately return the data requested by the user, with no syntax or logical errors (like joining on wrong columns or incorrect group by).\n"
        "Your response MUST be a JSON object with a single key 'correctness_score', a float between 0.0 (wrong query) and 1.0 (perfectly correct).\n"
        "Do not include any explanation or markdown code block wraps."
    )
    
    user_content = (
        f"Schema Context:\n{schema_context}\n\n"
        f"User Business Query: {query}\n\n"
        f"Generated SQL: {sql}"
    )
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            temperature=0.0
        )
        content = (response.choices[0].message.content or "").strip()
        if content.startswith("```"):
            content = content.replace("```json", "").replace("```", "").strip()
            
        data = json.loads(content)
        return float(data.get("correctness_score", 1.0))
    except Exception as e:
        print(f"Failed to evaluate SQL correctness: {e}")
        return 0.9  # Fallback score


async def compute_overall_confidence(
    query: str,
    route_decision: str,
    response_content: str,
    retrieved_chunks: list[str],
    sql_query: Optional[str],
    schema_context: Optional[str] = None
) -> dict[str, Any]:
    """
    Evaluate all facets of the response pipeline and compute a weighted confidence score.
    Returns a dict with all individual scores and the aggregated 'confidence_score'.
    """
    scores = {
        "faithfulness": 1.0,
        "relevance": 1.0,
        "sql_safety": 1.0,
        "sql_correctness": 1.0,
        "confidence_score": 1.0
    }
    
    # 1. Evaluate RAG components if applicable
    if route_decision in ("rag", "hybrid") and retrieved_chunks:
        scores["relevance"] = await evaluate_retrieval_relevance(query, retrieved_chunks)
        scores["faithfulness"] = await evaluate_faithfulness(response_content, retrieved_chunks)
        
    # 2. Evaluate SQL components if applicable
    if route_decision in ("sql", "hybrid", "analytics") and sql_query:
        scores["sql_safety"] = evaluate_sql_safety(sql_query)
        if schema_context:
            scores["sql_correctness"] = await evaluate_sql_correctness(query, sql_query, schema_context)
            
    # 3. Compute overall aggregated confidence score
    if route_decision == "rag":
        scores["confidence_score"] = round(0.4 * scores["relevance"] + 0.6 * scores["faithfulness"], 2)
    elif route_decision in ("sql", "analytics"):
        # If SQL fails safety completely, confidence is 0
        if scores["sql_safety"] == 0.0:
            scores["confidence_score"] = 0.0
        else:
            scores["confidence_score"] = round(scores["sql_correctness"], 2)
    elif route_decision == "hybrid":
        rag_component = 0.4 * scores["relevance"] + 0.6 * scores["faithfulness"]
        sql_component = scores["sql_correctness"] if scores["sql_safety"] > 0.0 else 0.0
        scores["confidence_score"] = round(0.5 * rag_component + 0.5 * sql_component, 2)
    else:
        # Generic direct LLM fallback
        scores["confidence_score"] = 1.0
        
    return scores
