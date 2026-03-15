import uuid
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.users import User
from app.models.messages import Message
from app.models.agent_runs import AgentRun
from app.schemas.chat import ChatRequest, ChatResponse, MessageResponse, AgentRunResponse, CitationResponse
from app.services import session_service
from app.services.agent_service import run_agent

router = APIRouter(tags=["chat"])


@router.get("/sessions/{session_id}/messages", response_model=List[MessageResponse])
def get_messages(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session_service.get_session(db, session_id, current_user.id)
    messages = (
        db.query(Message)
        .filter(
            Message.session_id == session_id,
            Message.user_id == current_user.id,
        )
        .order_by(Message.created_at.asc())
        .all()
    )
    return messages


@router.post("/sessions/{session_id}/chat", response_model=ChatResponse)
def chat(
    session_id: str,
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session_obj = session_service.get_session(db, session_id, current_user.id)
    llm_provider = getattr(session_obj, "llm_model", "gemini") or "gemini"

    # Save user message
    user_msg = Message(
        id=str(uuid.uuid4()),
        session_id=session_id,
        user_id=current_user.id,
        role="user",
        content=request.message,
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    # Create agent run record
    agent_run_id = str(uuid.uuid4())
    agent_run = AgentRun(
        id=agent_run_id,
        user_id=current_user.id,
        session_id=session_id,
        user_message_id=user_msg.id,
        status="pending",
    )
    db.add(agent_run)
    db.commit()

    # Run agent
    result = run_agent(
        db=db,
        session_id=session_id,
        user_id=current_user.id,
        user_message=request.message,
        agent_run_id=agent_run_id,
        llm_provider=llm_provider,
    )

    final_answer = result["final_answer"]
    citations_data = result["citations"]
    plan = result["plan"]
    clarification_needed = result["clarification_needed"]
    clarification_question = result["clarification_question"]
    artifacts = result.get("artifacts", [])

    # Build structured payload for assistant message
    structured_payload = {
        "plan": plan,
        "citations": citations_data,
        "agent_run_id": agent_run_id,
        "clarification_needed": clarification_needed,
        "clarification_question": clarification_question,
        "artifacts": artifacts,
    }

    # Save assistant message
    assistant_msg = Message(
        id=str(uuid.uuid4()),
        session_id=session_id,
        user_id=current_user.id,
        role="assistant",
        content=final_answer,
        structured_payload=structured_payload,
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    # Update session updated_at
    from app.models.sessions import Session as SessionModel
    sess = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if sess:
        sess.updated_at = datetime.utcnow()
        db.commit()

    citations = [
        CitationResponse(
            source_id=c.get("source_id", ""),
            source_name=c.get("source_name", ""),
            chunk_index=c.get("chunk_index", 0),
            excerpt=c.get("excerpt", ""),
        )
        for c in citations_data
    ]

    return ChatResponse(
        message_id=assistant_msg.id,
        session_id=session_id,
        role="assistant",
        content=final_answer,
        plan=plan,
        citations=citations,
        agent_run_id=agent_run_id,
        clarification_needed=clarification_needed,
        clarification_question=clarification_question,
        artifacts=artifacts,
        created_at=assistant_msg.created_at,
    )


@router.get("/sessions/{session_id}/agent-runs/{run_id}", response_model=AgentRunResponse)
def get_agent_run(
    session_id: str,
    run_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session_service.get_session(db, session_id, current_user.id)

    run = (
        db.query(AgentRun)
        .filter(
            AgentRun.id == run_id,
            AgentRun.session_id == session_id,
            AgentRun.user_id == current_user.id,
        )
        .first()
    )
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent run not found")

    return run
