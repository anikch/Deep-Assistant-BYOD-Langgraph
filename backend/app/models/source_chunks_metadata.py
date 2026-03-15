import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from app.db.session import Base


class SourceChunkMetadata(Base):
    __tablename__ = "source_chunks_metadata"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source_id = Column(String, ForeignKey("sources.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    vector_ref = Column(String(255), nullable=True)
    chunk_metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
