from datetime import datetime
from typing import Any, Optional
from uuid import UUID
from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[UUID] = None


class MessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    role: str
    content: str
    agent_name: Optional[str] = None
    sources_json: Optional[list[dict[str, Any]]] = None
    sql_query: Optional[str] = None
    chart_url: Optional[str] = None
    confidence_score: Optional[float] = None
    latency_ms: Optional[int] = None
    tokens_used: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConversationDetailResponse(ConversationResponse):
    messages: list[MessageResponse] = []


class ChatResponse(BaseModel):
    content: str
    conversation_id: UUID
    sources: Optional[list[dict[str, Any]]] = None
    sql_query: Optional[str] = None
    chart_url: Optional[str] = None
    confidence_score: Optional[float] = None
    agent_trace: Optional[list[dict[str, Any]]] = None
