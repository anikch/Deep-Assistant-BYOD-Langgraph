import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB
from app.db.session import Base


class Skill(Base):
    __tablename__ = "skills"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    version = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    skill_metadata_json = Column(JSONB, nullable=True)
    install_status = Column(String(50), default="installed")
    validation_status = Column(
        String(50), default="uploaded", nullable=False
    )  # uploaded/validating/valid/invalid/failed
    validation_errors = Column(JSONB, nullable=True)
    is_globally_enabled = Column(Boolean, default=True, nullable=False)
    storage_path = Column(String(1000), nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
