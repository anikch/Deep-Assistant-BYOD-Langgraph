import os
import shutil
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.agents.graph import get_agent_graph
from app.agents.state import AgentState
from app.models.messages import Message
from app.models.agent_runs import AgentRun
from app.models.artifacts import Artifact
from app.services.skill_loader import load_active_skills

logger = logging.getLogger(__name__)


def get_conversation_history(db: Session, session_id: str, user_id: str, limit: int = 20) -> List[Dict]:
    """Load recent conversation history for a session."""
    messages = (
        db.query(Message)
        .filter(
            Message.session_id == session_id,
            Message.user_id == user_id,
        )
        .order_by(Message.created_at.asc())
        .limit(limit)
        .all()
    )
    return [{"role": m.role, "content": m.content} for m in messages]


def run_agent(
    db: Session,
    session_id: str,
    user_id: str,
    user_message: str,
    agent_run_id: str,
    llm_provider: str = "gemini",
) -> Dict[str, Any]:
    """
    Invoke the LangGraph agent for a user message.
    Returns dict with: final_answer, citations, plan, clarification_needed, clarification_question
    """
    # Load conversation history
    history = get_conversation_history(db, session_id, user_id)

    # Load active skills
    active_skills = load_active_skills(db, user_id, session_id)

    # Build initial state
    initial_state: AgentState = {
        "user_message": user_message,
        "session_id": session_id,
        "user_id": user_id,
        "messages": history,
        "retrieved_chunks": [],
        "current_plan": [],
        "clarification_needed": False,
        "clarification_question": None,
        "selected_skills": [],
        "code_execution_needed": False,
        "execution_outputs": [],
        "final_answer": None,
        "citations": [],
        "plan_revision_count": 0,
        "agent_run_id": agent_run_id,
        "active_skills": active_skills,
        "llm_provider": llm_provider,
        "error": None,
    }

    # Update agent run status to running
    agent_run = db.query(AgentRun).filter(AgentRun.id == agent_run_id).first()
    if agent_run:
        agent_run.status = "running"
        db.commit()

    # Invoke LangGraph with thread_id=session_id for memory
    graph = get_agent_graph()
    config = {"configurable": {"thread_id": session_id}}

    try:
        result_state = graph.invoke(initial_state, config=config)

        final_answer = result_state.get("final_answer") or "I was unable to generate a response."
        citations = result_state.get("citations", [])
        plan = result_state.get("current_plan", [])
        clarification_needed = result_state.get("clarification_needed", False)
        clarification_question = result_state.get("clarification_question")

        # Register any output files produced by skill execution as artifacts
        artifacts = _register_skill_artifacts(
            db=db,
            user_id=user_id,
            session_id=session_id,
            execution_outputs=result_state.get("execution_outputs", []),
        )

        # Update agent run record
        if agent_run:
            agent_run.status = "complete"
            agent_run.current_plan = plan
            agent_run.final_summary = final_answer[:500] if final_answer else ""
            agent_run.completed_at = datetime.utcnow()
            db.commit()

        return {
            "final_answer": final_answer,
            "citations": citations,
            "plan": plan,
            "clarification_needed": clarification_needed,
            "clarification_question": clarification_question,
            "artifacts": artifacts,
        }

    except Exception as e:
        logger.error(f"Agent run {agent_run_id} failed: {e}", exc_info=True)
        if agent_run:
            agent_run.status = "failed"
            agent_run.completed_at = datetime.utcnow()
            db.commit()

        return {
            "final_answer": f"I encountered an error while processing your request: {str(e)}",
            "citations": [],
            "plan": [],
            "clarification_needed": False,
            "clarification_question": None,
            "artifacts": [],
        }


# Extension map for determining artifact_type from file extension
_EXT_TO_TYPE = {
    ".pptx": "pptx",
    ".pdf": "pdf",
    ".csv": "csv",
    ".xlsx": "xlsx",
}


def _register_skill_artifacts(
    db: Session,
    user_id: str,
    session_id: str,
    execution_outputs: List[Dict],
) -> List[Dict]:
    """
    For each successful skill execution that produced an output file,
    copy the file to artifact storage and register it in the DB.
    Returns a list of artifact dicts.
    """
    from app.core.config import settings

    registered = []
    for output in execution_outputs:
        if not output.get("success") or not output.get("output_file"):
            continue

        src_path = output["output_file"]
        if not os.path.exists(src_path):
            logger.warning(f"Skill output file not found: {src_path}")
            continue

        ext = os.path.splitext(src_path)[1].lower()
        artifact_type = _EXT_TO_TYPE.get(ext)
        if not artifact_type:
            logger.warning(f"Unsupported skill output extension: {ext}")
            continue

        artifact_id = str(uuid.uuid4())
        storage_dir = os.path.join(settings.storage_path, "artifacts", user_id, session_id)
        os.makedirs(storage_dir, exist_ok=True)
        dest_path = os.path.join(storage_dir, f"{artifact_id}{ext}")

        try:
            shutil.copy2(src_path, dest_path)
        except Exception as e:
            logger.error(f"Failed to copy skill output {src_path} → {dest_path}: {e}")
            continue

        skill_name = output.get("skill_name", "skill")
        display_name = f"{skill_name}_{artifact_id[:8]}"

        artifact = Artifact(
            id=artifact_id,
            user_id=user_id,
            session_id=session_id,
            artifact_type=artifact_type,
            display_name=display_name,
            file_path=dest_path,
            artifact_metadata={"skill_name": skill_name, "source_path": src_path},
        )
        db.add(artifact)
        db.commit()
        db.refresh(artifact)

        registered.append({
            "id": artifact_id,
            "display_name": display_name,
            "artifact_type": artifact_type,
            "skill_name": skill_name,
        })
        logger.info(f"Registered skill artifact: {artifact_id} ({artifact_type}) for session {session_id}")

    return registered
