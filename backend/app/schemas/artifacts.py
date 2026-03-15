from pydantic import BaseModel
from typing import Optional, Any, List
from datetime import datetime


class ArtifactGenerateRequest(BaseModel):
    artifact_type: str  # pdf/csv/xlsx
    display_name: str
    content: str  # the content/data to render
    columns: Optional[List[str]] = None  # for CSV/XLSX


class ArtifactResponse(BaseModel):
    id: str
    user_id: str
    session_id: str
    artifact_type: str
    display_name: str
    artifact_metadata: Optional[Any] = None
    created_at: datetime

    class Config:
        from_attributes = True
