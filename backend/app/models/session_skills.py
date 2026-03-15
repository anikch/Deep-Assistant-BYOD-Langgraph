import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from app.db.session import Base


class SessionSkill(Base):
    __tablename__ = "session_skills"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False, index=True)
    skill_id = Column(String, ForeignKey("skills.id"), nullable=False, index=True)
    is_enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("session_id", "skill_id", name="uq_session_skill"),
    )
