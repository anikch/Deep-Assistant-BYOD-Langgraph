import os
import uuid
import hashlib
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.users import User
from app.models.sources import Source, SourceType, IngestStatus
from app.schemas.sources import SourceResponse, AddURLRequest, AddTextRequest
from app.services import session_service
from app.ingestion.worker import process_source

router = APIRouter(tags=["sources"])

ALLOWED_EXTENSIONS = {
    "pdf": SourceType.pdf,
    "pptx": SourceType.pptx,
    "jpg": SourceType.image,
    "jpeg": SourceType.image,
    "png": SourceType.image,
    "txt": SourceType.txt,
}


def _count_file_url_sources(db: Session, session_id: str, user_id: str) -> int:
    return (
        db.query(Source)
        .filter(
            Source.session_id == session_id,
            Source.user_id == user_id,
            Source.source_type != SourceType.text,
        )
        .count()
    )


@router.get("/sessions/{session_id}/sources", response_model=List[SourceResponse])
def list_sources(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session_service.get_session(db, session_id, current_user.id)
    sources = (
        db.query(Source)
        .filter(Source.session_id == session_id, Source.user_id == current_user.id)
        .order_by(Source.created_at.desc())
        .all()
    )
    return sources


@router.post("/sessions/{session_id}/sources/upload", response_model=SourceResponse, status_code=status.HTTP_201_CREATED)
async def upload_source(
    session_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session_service.get_session(db, session_id, current_user.id)

    count = _count_file_url_sources(db, session_id, current_user.id)
    if count >= settings.max_files_and_urls_per_session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum of {settings.max_files_and_urls_per_session} files/URLs per session reached",
        )

    filename = file.filename or "upload"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{ext}' not allowed. Allowed: {list(ALLOWED_EXTENSIONS.keys())}",
        )

    source_type = ALLOWED_EXTENSIONS[ext]
    content = await file.read()

    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {settings.max_upload_mb}MB",
        )

    source_id = str(uuid.uuid4())
    content_hash = hashlib.sha256(content).hexdigest()

    storage_dir = os.path.join(
        settings.storage_path, "uploads", current_user.id, session_id, source_id
    )
    os.makedirs(storage_dir, exist_ok=True)
    local_path = os.path.join(storage_dir, filename)

    with open(local_path, "wb") as f:
        f.write(content)

    source = Source(
        id=source_id,
        user_id=current_user.id,
        session_id=session_id,
        source_type=source_type,
        display_name=filename,
        original_filename=filename,
        local_path=local_path,
        ingest_status=IngestStatus.pending,
        content_hash=content_hash,
    )
    db.add(source)
    db.commit()
    db.refresh(source)

    background_tasks.add_task(process_source, source_id)
    return source


@router.post("/sessions/{session_id}/sources/url", response_model=SourceResponse, status_code=status.HTTP_201_CREATED)
def add_url_source(
    session_id: str,
    request: AddURLRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session_service.get_session(db, session_id, current_user.id)

    count = _count_file_url_sources(db, session_id, current_user.id)
    if count >= settings.max_files_and_urls_per_session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum of {settings.max_files_and_urls_per_session} files/URLs per session reached",
        )

    display_name = request.display_name or request.url[:100]
    source = Source(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        session_id=session_id,
        source_type=SourceType.url,
        display_name=display_name,
        source_url=request.url,
        ingest_status=IngestStatus.pending,
    )
    db.add(source)
    db.commit()
    db.refresh(source)

    background_tasks.add_task(process_source, source.id)
    return source


@router.post("/sessions/{session_id}/sources/text", response_model=SourceResponse, status_code=status.HTTP_201_CREATED)
def add_text_source(
    session_id: str,
    request: AddTextRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session_service.get_session(db, session_id, current_user.id)

    if len(request.text) > settings.max_pasted_text_chars:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Text exceeds maximum of {settings.max_pasted_text_chars} characters",
        )

    source_id = str(uuid.uuid4())
    storage_dir = os.path.join(
        settings.storage_path, "uploads", current_user.id, session_id, source_id
    )
    os.makedirs(storage_dir, exist_ok=True)
    local_path = os.path.join(storage_dir, "pasted_text.txt")
    with open(local_path, "w", encoding="utf-8") as f:
        f.write(request.text)

    source = Source(
        id=source_id,
        user_id=current_user.id,
        session_id=session_id,
        source_type=SourceType.text,
        display_name=request.display_name,
        local_path=local_path,
        ingest_status=IngestStatus.pending,
        content_hash=hashlib.sha256(request.text.encode()).hexdigest(),
    )
    db.add(source)
    db.commit()
    db.refresh(source)

    background_tasks.add_task(process_source, source.id)
    return source


@router.delete("/sessions/{session_id}/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_source(
    session_id: str,
    source_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session_service.get_session(db, session_id, current_user.id)

    source = (
        db.query(Source)
        .filter(
            Source.id == source_id,
            Source.session_id == session_id,
            Source.user_id == current_user.id,
        )
        .first()
    )
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")

    # Delete from vector store
    try:
        from app.services.knowledge_store import KnowledgeStore
        ks = KnowledgeStore()
        ks.delete_source(session_id, source_id)
    except Exception as e:
        pass  # Best effort

    db.delete(source)
    db.commit()
