import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum
import enum
from app.db.session import Base


class SessionStatus(str, enum.Enum):
    active = "active"
    archived = "archived"
    deleted = "deleted"


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(500), nullable=False, default="New Session")
    status = Column(
        Enum(SessionStatus, name="session_status_enum"),
        default=SessionStatus.active,
        nullable=False,
    )
    llm_model = Column(String(100), nullable=False, default="gemini")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    archived_at = Column(DateTime, nullable=True)
