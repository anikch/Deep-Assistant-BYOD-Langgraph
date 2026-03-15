import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime
from app.db.session import Base


class PlatformSetting(Base):
    __tablename__ = "platform_settings"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    key = Column(String(255), unique=True, nullable=False, index=True)
    value = Column(String(1000), nullable=False)
    updated_by = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
