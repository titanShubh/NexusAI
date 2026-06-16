"""Chat conversation and streaming API routes."""

import json
import time
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sse_starlette.sse import EventSourceResponse

from app.dependencies import get_db, get_current_user
from app.db.models import User, Conversation, Message, QueryLog
from app.db.database import async_session_factory
from app.schemas.chat import ChatRequest, ChatResponse, ConversationResponse, ConversationDetailResponse
from app.agents.graph import compiled_graph

router = APIRouter(tags=["Chat"])


@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new chat conversation session."""
    conversation = Conversation(
        id=uuid4(),
        user_id=current_user.id,
        title="New Analytics Session"
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all conversations for the user."""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
    )
    return result.scalars().all()


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get conversation details with all historical messages."""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.id == conversation_id, Conversation.user_id == current_user.id)
        .options(selectinload(Conversation.messages))
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found."
        )
    # Sort messages by creation time
    conversation.messages.sort(key=lambda m: m.created_at)
    return conversation


@router.post("/chat")
async def chat_interaction(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Standard synchronous chat endpoint. Runs the LangGraph agent workflow
    and returns the compiled response.
    """
    start_time = time.time()
    
    # 1. Resolve conversation
    conv_id = request.conversation_id
    if not conv_id:
        conversation = Conversation(user_id=current_user.id, title=request.message[:30] + "...")
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        conv_id = conversation.id
    else:
        # Verify ownership
        result = await db.execute(
            select(Conversation).where(Conversation.id == conv_id, Conversation.user_id == current_user.id)
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found.")
            
    # 2. Save user message
    user_msg = Message(
        id=uuid4(),
        conversation_id=conv_id,
        role="user",
        content=request.message
    )
    db.add(user_msg)
    await db.commit()
    
    # 3. Compile historical messages for context
    msg_history_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conv_id)
        .order_by(Message.created_at.asc())
    )
    history = [{"role": m.role, "content": m.content} for m in msg_history_result.scalars().all()]

    # 4. Prepare state
    initial_state = {
        "messages": history,
        "conversation_id": conv_id,
        "user_id": current_user.id,
        "original_query": request.message,
        "decomposed_queries": [],
        "route_decision": None,
        "guardrail_flags": [],
        "rag_results": [],
        "sql_query": None,
        "sql_results": [],
        "chart_base64": None,
        "eval_scores": {},
        "final_response": None,
        "agent_trace": []
    }
    
    # 5. Run the graph
    try:
        final_state = await compiled_graph.ainvoke(initial_state)
    except Exception as e:
        print(f"Graph execution failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Orchestration failure: {e}"
        )
        
    latency_ms = int((time.time() - start_time) * 1000)
    
    # Calculate tokens used from trace
    tokens_used = sum(t.get("tokens_used", 0) for t in final_state.get("agent_trace", []))
    
    # Format sources for DB
    sources = []
    for chunk in final_state.get("rag_results", []):
        meta = chunk.get("metadata") or {}
        sources.append({
            "filename": meta.get("source", "Unknown"),
            "page_number": chunk.get("page_number", 1),
            "chunk_type": chunk.get("chunk_type", "text")
        })

    # 6. Save assistant response
    assistant_msg = Message(
        id=uuid4(),
        conversation_id=conv_id,
        role="assistant",
        content=final_state["final_response"] or "No response could be compiled.",
        agent_name="NexusOrchestrator",
        sources_json=sources,
        sql_query=final_state.get("sql_query"),
        chart_url=final_state.get("chart_base64"),
        confidence_score=final_state.get("eval_scores", {}).get("confidence_score", 1.0),
        latency_ms=latency_ms,
        tokens_used=tokens_used
    )
    db.add(assistant_msg)
    
    # 7. Update conversation title if default
    if conversation.title == "New Analytics Session":
        conversation.title = request.message[:40] + ("..." if len(request.message) > 40 else "")
        db.add(conversation)
        
    # 8. Create query log
    query_log = QueryLog(
        conversation_id=conv_id,
        original_query=request.message,
        decomposed_queries=final_state.get("decomposed_queries"),
        route_decision=final_state.get("route_decision", "direct"),
        eval_scores=final_state.get("eval_scores"),
        total_latency_ms=latency_ms
    )
    db.add(query_log)
    
    await db.commit()
    
    return ChatResponse(
        content=assistant_msg.content,
        conversation_id=conv_id,
        sources=sources,
        sql_query=assistant_msg.sql_query,
        chart_url=assistant_msg.chart_url,
        confidence_score=assistant_msg.confidence_score,
        agent_trace=final_state.get("agent_trace", [])
    )


@router.post("/chat/stream")
async def chat_interaction_stream(
    request: ChatRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Server-Sent Events (SSE) streaming chat endpoint.
    Streams progress traces of agent nodes as they run, and then outputs
    the final compiled response, data, and charts.
    """
    async def sse_generator():
        start_time = time.time()
        conv_id = request.conversation_id
        
        async with async_session_factory() as db:
            # 1. Resolve conversation
            if not conv_id:
                conversation = Conversation(user_id=current_user.id, title=request.message[:30] + "...")
                db.add(conversation)
                await db.commit()
                await db.refresh(conversation)
                conv_id = conversation.id
            else:
                result = await db.execute(
                    select(Conversation).where(Conversation.id == conv_id, Conversation.user_id == current_user.id)
                )
                conversation = result.scalar_one_or_none()
                if not conversation:
                    yield {"event": "error", "data": "Conversation not found."}
                    return
            
            # 2. Save user message
            user_msg = Message(id=uuid4(), conversation_id=conv_id, role="user", content=request.message)
            db.add(user_msg)
            await db.commit()
            
            # Fetch message history
            history_result = await db.execute(
                select(Message).where(Message.conversation_id == conv_id).order_by(Message.created_at.asc())
            )
            history = [{"role": m.role, "content": m.content} for m in history_result.scalars().all()]
            
        # Send start event
        yield {"event": "start", "data": json.dumps({"conversation_id": str(conv_id)})}
        
        # 3. Build state
        state = {
            "messages": history,
            "conversation_id": conv_id,
            "user_id": current_user.id,
            "original_query": request.message,
            "decomposed_queries": [],
            "route_decision": None,
            "guardrail_flags": [],
            "rag_results": [],
            "sql_query": None,
            "sql_results": [],
            "chart_base64": None,
            "eval_scores": {},
            "final_response": None,
            "agent_trace": []
        }
        
        # 4. Stream LangGraph execution updates
        try:
            async for chunk in compiled_graph.astream(state, stream_mode="updates"):
                for node_name, state_update in chunk.items():
                    # Apply updates to local accumulator state
                    for k, v in state_update.items():
                        if k in ("messages", "agent_trace") and state[k]:
                            state[k] = state[k] + v
                        else:
                            state[k] = v
                    
                    # Yield step event
                    trace_list = state_update.get("agent_trace", [])
                    node_trace = trace_list[-1] if trace_list else {"node_name": node_name, "status": "success"}
                    
                    yield {
                        "event": "step",
                        "data": json.dumps({
                            "node_name": node_trace.get("node_name", node_name),
                            "status": node_trace.get("status", "success"),
                            "latency_ms": node_trace.get("latency_ms", 0)
                        })
                    }
        except Exception as e:
            print(f"Streaming graph error: {e}")
            yield {"event": "error", "data": f"Graph processing failed: {str(e)}"}
            return
            
        latency_ms = int((time.time() - start_time) * 1000)
        tokens_used = sum(t.get("tokens_used", 0) for t in state.get("agent_trace", []))
        
        # Format sources
        sources = []
        for chunk in state.get("rag_results", []):
            meta = chunk.get("metadata") or {}
            sources.append({
                "filename": meta.get("source", "Unknown"),
                "page_number": chunk.get("page_number", 1),
                "chunk_type": chunk.get("chunk_type", "text")
            })
            
        # 5. Save assistant response & logs in DB
        async with async_session_factory() as db:
            assistant_msg = Message(
                id=uuid4(),
                conversation_id=conv_id,
                role="assistant",
                content=state["final_response"] or "No response could be compiled.",
                agent_name="NexusOrchestrator",
                sources_json=sources,
                sql_query=state.get("sql_query"),
                chart_url=state.get("chart_base64"),
                confidence_score=state.get("eval_scores", {}).get("confidence_score", 1.0),
                latency_ms=latency_ms,
                tokens_used=tokens_used
            )
            db.add(assistant_msg)
            
            # Update title
            refetched_conv_result = await db.execute(select(Conversation).where(Conversation.id == conv_id))
            refetched_conv = refetched_conv_result.scalar_one()
            if refetched_conv.title == "New Analytics Session":
                refetched_conv.title = request.message[:40] + ("..." if len(request.message) > 40 else "")
                db.add(refetched_conv)
                
            query_log = QueryLog(
                conversation_id=conv_id,
                original_query=request.message,
                decomposed_queries=state.get("decomposed_queries"),
                route_decision=state.get("route_decision", "direct"),
                eval_scores=state.get("eval_scores"),
                total_latency_ms=latency_ms
            )
            db.add(query_log)
            await db.commit()
            
        # 6. Yield final results
        yield {
            "event": "final",
            "data": json.dumps({
                "content": assistant_msg.content,
                "sources": sources,
                "sql_query": assistant_msg.sql_query,
                "chart_url": assistant_msg.chart_url,
                "confidence_score": assistant_msg.confidence_score,
                "agent_trace": state.get("agent_trace", [])
            })
        }
        
    return EventSourceResponse(sse_generator())
