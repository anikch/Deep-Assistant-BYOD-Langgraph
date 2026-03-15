import os
import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from app.models.skills import Skill
from app.models.session_skills import SessionSkill

logger = logging.getLogger(__name__)


def load_active_skills(db: Session, user_id: str, session_id: str) -> List[Dict[str, Any]]:
    """
    Load active skills for a session.
    Skills must be:
    - Owned by user
    - Globally enabled
    - Valid
    - Enabled for this session (or not yet configured for session)
    """
    # Get all valid, globally enabled skills for user
    valid_skills = (
        db.query(Skill)
        .filter(
            Skill.user_id == user_id,
            Skill.is_globally_enabled == True,
            Skill.validation_status == "valid",
        )
        .all()
    )

    if not valid_skills:
        return []

    # Get session-level skill enables
    skill_ids = [s.id for s in valid_skills]
    session_skill_map = {}
    session_skills = (
        db.query(SessionSkill)
        .filter(
            SessionSkill.session_id == session_id,
            SessionSkill.skill_id.in_(skill_ids),
        )
        .all()
    )
    for ss in session_skills:
        session_skill_map[ss.skill_id] = ss.is_enabled

    active = []
    for skill in valid_skills:
        # If session skill record exists, use its is_enabled value
        # If not, default to enabled (globally enabled skill is available)
        is_enabled = session_skill_map.get(skill.id, True)
        if not is_enabled:
            continue

        # Load SKILL.md content
        skill_content = _load_skill_md(skill.storage_path)

        active.append({
            "id": skill.id,
            "name": skill.name,
            "version": skill.version,
            "description": skill.description,
            "skill_content": skill_content,
            "metadata": skill.skill_metadata_json,
        })

    return active


def _load_skill_md(storage_path: str) -> str:
    """Load SKILL.md content from storage path."""
    if not storage_path:
        return ""
    skill_md_path = os.path.join(storage_path, "SKILL.md")
    try:
        if os.path.exists(skill_md_path):
            with open(skill_md_path, "r", encoding="utf-8") as f:
                return f.read()
    except Exception as e:
        logger.error(f"Failed to load SKILL.md from {storage_path}: {e}")
    return ""
