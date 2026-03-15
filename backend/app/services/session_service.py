import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.sessions import Session as SessionModel, SessionStatus


def create_session(db: Session, user_id: str, title: str = "New Session", llm_model: str = "gemini") -> SessionModel:
    session = SessionModel(
        id=str(uuid.uuid4()),
        user_id=user_id,
        title=title,
        status=SessionStatus.active,
        llm_model=llm_model,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_session(db: Session, session_id: str, user_id: str) -> SessionModel:
    session = (
        db.query(SessionModel)
        .filter(
            SessionModel.id == session_id,
            SessionModel.user_id == user_id,
            SessionModel.status != SessionStatus.deleted,
        )
        .first()
    )
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session


def list_sessions(db: Session, user_id: str, include_archived: bool = False) -> List[SessionModel]:
    q = db.query(SessionModel).filter(
        SessionModel.user_id == user_id,
        SessionModel.status != SessionStatus.deleted,
    )
    if not include_archived:
        q = q.filter(SessionModel.status == SessionStatus.active)
    return q.order_by(SessionModel.updated_at.desc()).all()


def update_session(
    db: Session,
    session_id: str,
    user_id: str,
    title: Optional[str] = None,
    status: Optional[str] = None,
) -> SessionModel:
    session = get_session(db, session_id, user_id)

    if title is not None:
        session.title = title
    if status is not None:
        session.status = SessionStatus(status)
        if status == "archived":
            session.archived_at = datetime.utcnow()

    session.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(session)
    return session


def delete_session(db: Session, session_id: str, user_id: str) -> None:
    session = get_session(db, session_id, user_id)
    session.status = SessionStatus.deleted
    session.updated_at = datetime.utcnow()
    db.commit()
