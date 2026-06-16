"""RAG Search agent node for retrieval and synthesis."""

import json
import time
from typing import Any
from sqlalchemy import select
from openai import AsyncOpenAI
from langchain_openai import OpenAIEmbeddings
import cohere

from app.config import get_settings
from app.db.database import async_session_factory
from app.db.models import Document
from app.agents.state import NexusState
from app.agents.prompts.system_prompts import RAG_SYSTEM_PROMPT
from app.services.vector_service import get_qdrant_client, search_vectors

settings = get_settings()


async def rag_node(state: NexusState) -> dict[str, Any]:
    """
    RAG node: queries Qdrant vectors, performs Cohere reranking, and synthesizes grounded answer.
    """
    start_time = time.time()
    
    # 1. Skip if RAG is not required
    route = state.get("route_decision")
    if route not in ("rag", "hybrid"):
        trace = {
            "node_name": "RAGAgent",
            "status": "skipped",
            "latency_ms": 0,
            "tokens_used": 0,
            "metadata": {"reason": f"Route '{route}' does not require RAG."}
        }
        return {
            "rag_results": [],
            "agent_trace": [trace]
        }
        
    user_id = state["user_id"]
    decomposed_queries = state.get("decomposed_queries") or [state["original_query"]]
    
    # 2. Get user documents for filtering and type detection
    async with async_session_factory() as db:
        result = await db.execute(
            select(Document)
            .where(Document.user_id == user_id, Document.upload_status == "completed")
        )
        user_docs = result.scalars().all()
        document_ids = [d.id for d in user_docs]
        has_csv = any(d.file_type == "csv" for d in user_docs)
        
    if not document_ids:
        trace = {
            "node_name": "RAGAgent",
            "status": "success",
            "latency_ms": int((time.time() - start_time) * 1000),
            "tokens_used": 0,
            "metadata": {"reason": "No documents uploaded."}
        }
        return {
            "rag_results": [],
            "agent_trace": [trace]
        }
        
    qdrant = get_qdrant_client()
    embeddings_model = OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=settings.openai_api_key
    )
    
    all_hits = []
    vector_limit = 20 if has_csv else 8
    top_n = 15 if has_csv else 5
    
    # 3. Retrieve chunks for all decomposed queries
    for sub_query in decomposed_queries:
        try:
            query_vector = await embeddings_model.aembed_query(sub_query)
            hits = search_vectors(
                client=qdrant,
                query_vector=query_vector,
                limit=vector_limit,
                document_ids=document_ids
            )
            all_hits.extend(hits)
        except Exception as e:
            print(f"Error searching vector DB for '{sub_query}': {e}")
            
    # Deduplicate hits by chunk ID
    seen = set()
    deduped_hits = []
    for hit in all_hits:
        if hit["chunk_id"] not in seen:
            seen.add(hit["chunk_id"])
            deduped_hits.append(hit)
            
    if not deduped_hits:
        trace = {
            "node_name": "RAGAgent",
            "status": "success",
            "latency_ms": int((time.time() - start_time) * 1000),
            "tokens_used": 0,
            "metadata": {"reason": "No matching vector results."}
        }
        return {
            "rag_results": [],
            "agent_trace": [trace]
        }
        
    # 4. Cohere Reranking
    reranked_hits = deduped_hits
    if settings.cohere_api_key and len(deduped_hits) > 1:
        try:
            co = cohere.Client(api_key=settings.cohere_api_key)
            doc_contents = [h["content"] for h in deduped_hits]
            rerank_resp = co.rerank(
                query=state["original_query"],
                documents=doc_contents,
                top_n=min(top_n, len(deduped_hits)),
                model="rerank-english-v3.0"
            )
            reranked_hits = []
            for item in rerank_resp.results:
                hit = deduped_hits[item.index]
                hit["score"] = float(item.relevance_score)  # update with rerank score
                reranked_hits.append(hit)
        except Exception as e:
            print(f"Cohere rerank failed (falling back to vector score): {e}")
            # Fallback to top vector results
            deduped_hits.sort(key=lambda x: x["score"], reverse=True)
            reranked_hits = deduped_hits[:top_n]
    else:
        # Sort and take top
        deduped_hits.sort(key=lambda x: x["score"], reverse=True)
        reranked_hits = deduped_hits[:top_n]
        
    # 5. Synthesize answer using GPT-4o
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    
    # Format chunks text
    context_parts = []
    for h in reranked_hits:
        meta = h.get("metadata") or {}
        source = meta.get("source", "Unknown Document")
        context_parts.append(
            f"Document: {source}\n"
            f"Page: {h['page_number']}\n"
            f"Type: {h['chunk_type']}\n"
            f"Content:\n{h['content']}"
        )
    context_text = "\n\n".join(context_parts)
    
    tokens = 0
    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": RAG_SYSTEM_PROMPT.format(context_text=context_text)},
                {"role": "user", "content": f"Query: {state['original_query']}"}
            ],
            temperature=0.0
        )
        rag_answer = response.choices[0].message.content or ""
        tokens = response.usage.total_tokens if response.usage else 0
    except Exception as e:
        print(f"RAG LLM synthesis error: {e}")
        rag_answer = "Error generating document search response."

    latency = int((time.time() - start_time) * 1000)
    
    trace = {
        "node_name": "RAGAgent",
        "status": "success",
        "latency_ms": latency,
        "tokens_used": tokens,
        "metadata": {
            "reranked_chunks_count": len(reranked_hits),
            "citations": [{"source": h.get("metadata", {}).get("source"), "page": h["page_number"]} for h in reranked_hits]
        }
    }
    
    # Extract structured data if the query asks for a chart/graph
    query_lower = state["original_query"].lower()
    has_chart_intent = any(w in query_lower for w in ("plot", "chart", "graph", "visualize", "histogram"))
    
    extracted_sql_results = []
    if has_chart_intent:
        try:
            system_prompt = (
                "You are a data extraction assistant.\n"
                "The user wants to plot a chart based on the query and the text below.\n"
                "Extract the tabular data (categories and numeric values) from the text that should be plotted.\n"
                "Your response MUST be a JSON list of objects, where each object represents a data row to be plotted.\n"
                "For example, if plotting questions vs topic: [{\"topic\": \"recursion\", \"count\": 2}, ...]\n"
                "Return ONLY the raw JSON list, no markdown formatting, no explanations, no wrappers."
            )
            
            user_content = (
                f"Query: {state['original_query']}\n\n"
                f"Text Context:\n{rag_answer}"
            )
            
            resp = await client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.0
            )
            content = (resp.choices[0].message.content or "").strip()
            if content.startswith("```"):
                content = content.replace("```json", "").replace("```", "").strip()
            
            extracted_sql_results = json.loads(content)
            if not isinstance(extracted_sql_results, list):
                extracted_sql_results = []
        except Exception as e:
            print(f"Failed to extract structured data for plotting from RAG: {e}")

    # We store synthesized answer in state rag_results as a metadata field or standard state item
    return {
        "rag_results": reranked_hits,
        "sql_results": extracted_sql_results,  # Populate for the analytics agent
        # We append a message representing RAG's output so response gen can read it
        "messages": state.get("messages", []) + [{"role": "assistant", "content": rag_answer, "name": "RAGAgent"}],
        "agent_trace": [trace]
    }
