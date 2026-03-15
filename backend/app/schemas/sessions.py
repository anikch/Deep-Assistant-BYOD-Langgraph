from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class SessionCreate(BaseModel):
    title: str = "New Session"
    llm_model: str = "gemini"


class SessionUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None


class SessionResponse(BaseModel):
    id: str
    user_id: str
    title: str
    status: str
    llm_model: str
    created_at: datetime
    updated_at: datetime
    archived_at: Optional[datetime] = None

    class Config:
        from_attributes = True
