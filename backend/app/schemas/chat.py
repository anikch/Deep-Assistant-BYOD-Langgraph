from pydantic import BaseModel
from typing import Optional, List, Any, Dict
from datetime import datetime


class ChatRequest(BaseModel):
    message: str
    clarification_response: Optional[str] = None


class CitationResponse(BaseModel):
    source_id: str
    source_name: str
    chunk_index: int
    excerpt: str


class ChatResponse(BaseModel):
    message_id: str
    session_id: str
    role: str
    content: str
    plan: Optional[List[str]] = None
    citations: Optional[List[CitationResponse]] = None
    agent_run_id: Optional[str] = None
    clarification_needed: bool = False
    clarification_question: Optional[str] = None
    artifacts: Optional[List[Dict]] = None
    created_at: datetime


class MessageResponse(BaseModel):
    id: str
    session_id: str
    user_id: str
    role: str
    content: str
    structured_payload: Optional[Any] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AgentRunResponse(BaseModel):
    id: str
    user_id: str
    session_id: str
    status: str
    current_plan: Optional[List[str]] = None
    final_summary: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
