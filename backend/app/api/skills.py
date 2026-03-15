import io
import os
import uuid
import zipfile
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.users import User
from app.models.skills import Skill
from app.models.session_skills import SessionSkill
from app.schemas.skills import SkillResponse, SessionSkillResponse
from app.services.skill_validator import validate_skill_zip, parse_skill_metadata
from app.services import session_service

router = APIRouter(tags=["skills"])


@router.get("/skills", response_model=List[SkillResponse])
def list_skills(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Skill)
        .filter(Skill.user_id == current_user.id)
        .order_by(Skill.uploaded_at.desc())
        .all()
    )


@router.post("/skills/upload", response_model=SkillResponse, status_code=status.HTTP_201_CREATED)
async def upload_skill(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not settings.enable_skills:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Skills are disabled")

    content = await file.read()
    size_mb = len(content) / (1024 * 1024)

    is_valid, errors = validate_skill_zip(content, size_mb)
    metadata = parse_skill_metadata(content)

    skill_id = str(uuid.uuid4())
    storage_dir = os.path.join(settings.storage_path, "skills", current_user.id, skill_id)
    os.makedirs(storage_dir, exist_ok=True)

    if is_valid:
        # Unpack ZIP to storage
        zf = zipfile.ZipFile(io.BytesIO(content))
        zf.extractall(storage_dir)
        zf.close()

    skill = Skill(
        id=skill_id,
        user_id=current_user.id,
        name=metadata.get("name", file.filename or "Unknown Skill"),
        version=metadata.get("version", "1.0"),
        description=metadata.get("description", ""),
        skill_metadata_json=metadata,
        install_status="installed" if is_valid else "failed",
        validation_status="valid" if is_valid else "invalid",
        validation_errors=errors if errors else None,
        is_globally_enabled=True if is_valid else False,
        storage_path=storage_dir if is_valid else None,
    )
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill


@router.get("/skills/{skill_id}", response_model=SkillResponse)
def get_skill(
    skill_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    skill = db.query(Skill).filter(Skill.id == skill_id, Skill.user_id == current_user.id).first()
    if not skill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
    return skill


@router.post("/skills/{skill_id}/enable", response_model=SkillResponse)
def enable_skill(
    skill_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    skill = db.query(Skill).filter(Skill.id == skill_id, Skill.user_id == current_user.id).first()
    if not skill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
    skill.is_globally_enabled = True
    db.commit()
    db.refresh(skill)
    return skill


@router.post("/skills/{skill_id}/disable", response_model=SkillResponse)
def disable_skill(
    skill_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    skill = db.query(Skill).filter(Skill.id == skill_id, Skill.user_id == current_user.id).first()
    if not skill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
    skill.is_globally_enabled = False
    db.commit()
    db.refresh(skill)
    return skill


@router.delete("/skills/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_skill(
    skill_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    skill = db.query(Skill).filter(Skill.id == skill_id, Skill.user_id == current_user.id).first()
    if not skill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")

    # Delete storage
    if skill.storage_path and os.path.exists(skill.storage_path):
        import shutil
        shutil.rmtree(skill.storage_path, ignore_errors=True)

    # Delete session skills
    db.query(SessionSkill).filter(SessionSkill.skill_id == skill_id).delete()
    db.delete(skill)
    db.commit()


@router.post("/sessions/{session_id}/skills/{skill_id}/enable", response_model=SessionSkillResponse)
def enable_session_skill(
    session_id: str,
    skill_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session_service.get_session(db, session_id, current_user.id)
    skill = db.query(Skill).filter(Skill.id == skill_id, Skill.user_id == current_user.id).first()
    if not skill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")

    ss = (
        db.query(SessionSkill)
        .filter(SessionSkill.session_id == session_id, SessionSkill.skill_id == skill_id)
        .first()
    )
    if ss:
        ss.is_enabled = True
    else:
        ss = SessionSkill(
            id=str(uuid.uuid4()),
            session_id=session_id,
            skill_id=skill_id,
            is_enabled=True,
        )
        db.add(ss)
    db.commit()
    db.refresh(ss)
    return ss


@router.post("/sessions/{session_id}/skills/{skill_id}/disable", response_model=SessionSkillResponse)
def disable_session_skill(
    session_id: str,
    skill_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session_service.get_session(db, session_id, current_user.id)
    skill = db.query(Skill).filter(Skill.id == skill_id, Skill.user_id == current_user.id).first()
    if not skill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")

    ss = (
        db.query(SessionSkill)
        .filter(SessionSkill.session_id == session_id, SessionSkill.skill_id == skill_id)
        .first()
    )
    if ss:
        ss.is_enabled = False
        db.commit()
        db.refresh(ss)
    else:
        ss = SessionSkill(
            id=str(uuid.uuid4()),
            session_id=session_id,
            skill_id=skill_id,
            is_enabled=False,
        )
        db.add(ss)
        db.commit()
        db.refresh(ss)
    return ss
