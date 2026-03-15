from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


class SkillResponse(BaseModel):
    id: str
    user_id: str
    name: str
    version: Optional[str] = None
    description: Optional[str] = None
    skill_metadata_json: Optional[Any] = None
    install_status: Optional[str] = None
    validation_status: str
    validation_errors: Optional[Any] = None
    is_globally_enabled: bool
    uploaded_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SessionSkillResponse(BaseModel):
    id: str
    session_id: str
    skill_id: str
    is_enabled: bool
    created_at: datetime

    class Config:
        from_attributes = True
