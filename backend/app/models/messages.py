import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import JSONB
from app.db.session import Base


class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String(50), nullable=False)  # user / assistant / system
    content = Column(Text, nullable=False, default="")
    structured_payload = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
