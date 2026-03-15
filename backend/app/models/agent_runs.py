import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from app.db.session import Base


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False, index=True)
    user_message_id = Column(String, ForeignKey("messages.id"), nullable=True)
    status = Column(String(50), default="pending", nullable=False)  # pending/running/complete/failed
    current_plan = Column(JSONB, nullable=True)
    final_summary = Column(Text, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
