from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime


class SourceResponse(BaseModel):
    id: str
    user_id: str
    session_id: str
    source_type: str
    display_name: str
    original_filename: Optional[str] = None
    source_url: Optional[str] = None
    ingest_status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AddURLRequest(BaseModel):
    url: str
    display_name: Optional[str] = None


class AddTextRequest(BaseModel):
    text: str
    display_name: str = "Pasted Text"
