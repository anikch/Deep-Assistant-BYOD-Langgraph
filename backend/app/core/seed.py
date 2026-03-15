import logging
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password

logger = logging.getLogger(__name__)


def seed_admin_user(db: Session) -> None:
    if not settings.seed_admin_user:
        return

    from app.models.users import User
    import uuid

    existing = db.query(User).filter(User.username == settings.seed_admin_username).first()
    if existing:
        logger.info(f"Admin user '{settings.seed_admin_username}' already exists.")
        return

    admin = User(
        id=str(uuid.uuid4()),
        username=settings.seed_admin_username,
        password_hash=hash_password(settings.seed_admin_password),
        is_active=True,
        is_admin=True,
    )
    db.add(admin)
    db.commit()
    logger.info(f"Admin user '{settings.seed_admin_username}' created.")
