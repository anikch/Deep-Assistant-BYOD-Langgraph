import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from app.db.session import Base


class ToolRun(Base):
    __tablename__ = "tool_runs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_run_id = Column(String, ForeignKey("agent_runs.id"), nullable=False, index=True)
    tool_name = Column(String(255), nullable=False)
    input_json = Column(JSONB, nullable=True)
    output_json = Column(JSONB, nullable=True)
    status = Column(String(50), default="pending", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
