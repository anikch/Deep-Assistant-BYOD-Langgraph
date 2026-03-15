import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum
import enum
from app.db.session import Base


class SourceType(str, enum.Enum):
    pdf = "pdf"
    pptx = "pptx"
    image = "image"
    txt = "txt"
    text = "text"
    url = "url"


class IngestStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    complete = "complete"
    failed = "failed"


class Source(Base):
    __tablename__ = "sources"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False, index=True)
    source_type = Column(
        Enum(SourceType, name="source_type_enum"),
        nullable=False,
    )
    display_name = Column(String(500), nullable=False)
    original_filename = Column(String(500), nullable=True)
    source_url = Column(String(2000), nullable=True)
    local_path = Column(String(1000), nullable=True)
    ingest_status = Column(
        Enum(IngestStatus, name="ingest_status_enum"),
        default=IngestStatus.pending,
        nullable=False,
    )
    content_hash = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
