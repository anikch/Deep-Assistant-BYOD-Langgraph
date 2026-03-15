import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from app.db.session import Base


class Artifact(Base):
    __tablename__ = "artifacts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False, index=True)
    artifact_type = Column(String(20), nullable=False)  # pdf/csv/xlsx
    display_name = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=True)
    artifact_metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
