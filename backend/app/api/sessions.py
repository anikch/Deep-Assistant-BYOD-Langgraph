from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.users import User
from app.schemas.sessions import SessionCreate, SessionUpdate, SessionResponse
from app.services import session_service
from app.core.llm_provider import AVAILABLE_LLM_MODELS

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("/llm-models")
def list_llm_models():
    """Return the list of available LLM models for session creation."""
    return AVAILABLE_LLM_MODELS


@router.get("", response_model=List[SessionResponse])
def list_sessions(
    include_archived: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sessions = session_service.list_sessions(db, current_user.id, include_archived)
    return sessions


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    request: SessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return session_service.create_session(db, current_user.id, request.title, request.llm_model)


@router.get("/{session_id}", response_model=SessionResponse)
def get_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return session_service.get_session(db, session_id, current_user.id)


@router.patch("/{session_id}", response_model=SessionResponse)
def update_session(
    session_id: str,
    request: SessionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return session_service.update_session(
        db, session_id, current_user.id, title=request.title, status=request.status
    )


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session_service.delete_session(db, session_id, current_user.id)
