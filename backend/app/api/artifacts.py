import os
import uuid
import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.users import User
from app.models.artifacts import Artifact
from app.schemas.artifacts import ArtifactGenerateRequest, ArtifactResponse
from app.services import session_service

router = APIRouter(tags=["artifacts"])


def _generate_pdf(content: str, output_path: str) -> None:
    """Generate a formatted PDF from text content using reportlab."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib import colors

    doc = SimpleDocTemplate(output_path, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    # Title style
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Title"],
        fontSize=16,
        textColor=colors.HexColor("#1a1a2e"),
        spaceAfter=20,
    )

    body_style = ParagraphStyle(
        "CustomBody",
        parent=styles["Normal"],
        fontSize=11,
        leading=16,
        spaceAfter=10,
    )

    # Process content lines
    lines = content.split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            story.append(Spacer(1, 6))
            continue
        if line.startswith("# "):
            story.append(Paragraph(line[2:], title_style))
        elif line.startswith("## "):
            story.append(Paragraph(line[3:], styles["Heading2"]))
        elif line.startswith("### "):
            story.append(Paragraph(line[4:], styles["Heading3"]))
        else:
            # Escape HTML entities
            safe_line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            story.append(Paragraph(safe_line, body_style))

    doc.build(story)


def _generate_csv(content: str, output_path: str, columns: List[str] = None) -> None:
    """Generate CSV from content."""
    import pandas as pd

    # Try to parse content as JSON array
    try:
        data = json.loads(content)
        if isinstance(data, list):
            df = pd.DataFrame(data)
        elif isinstance(data, dict):
            df = pd.DataFrame([data])
        else:
            df = pd.DataFrame({"content": [content]})
    except json.JSONDecodeError:
        # Parse as line-by-line text
        lines = [l.strip() for l in content.split("\n") if l.strip()]
        if columns:
            rows = []
            for line in lines:
                parts = line.split(",")
                row = {col: parts[i].strip() if i < len(parts) else "" for i, col in enumerate(columns)}
                rows.append(row)
            df = pd.DataFrame(rows, columns=columns)
        else:
            df = pd.DataFrame({"content": lines})

    df.to_csv(output_path, index=False)


def _generate_xlsx(content: str, output_path: str, columns: List[str] = None) -> None:
    """Generate XLSX from content."""
    import pandas as pd

    try:
        data = json.loads(content)
        if isinstance(data, list):
            df = pd.DataFrame(data)
        elif isinstance(data, dict):
            df = pd.DataFrame([data])
        else:
            df = pd.DataFrame({"content": [content]})
    except json.JSONDecodeError:
        lines = [l.strip() for l in content.split("\n") if l.strip()]
        if columns:
            rows = []
            for line in lines:
                parts = line.split(",")
                row = {col: parts[i].strip() if i < len(parts) else "" for i, col in enumerate(columns)}
                rows.append(row)
            df = pd.DataFrame(rows, columns=columns)
        else:
            df = pd.DataFrame({"content": lines})

    df.to_excel(output_path, index=False)


@router.get("/sessions/{session_id}/artifacts", response_model=List[ArtifactResponse])
def list_artifacts(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session_service.get_session(db, session_id, current_user.id)
    return (
        db.query(Artifact)
        .filter(Artifact.session_id == session_id, Artifact.user_id == current_user.id)
        .order_by(Artifact.created_at.desc())
        .all()
    )


@router.post("/sessions/{session_id}/artifacts/generate", response_model=ArtifactResponse, status_code=status.HTTP_201_CREATED)
def generate_artifact(
    session_id: str,
    request: ArtifactGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session_service.get_session(db, session_id, current_user.id)

    if request.artifact_type not in ("pdf", "csv", "xlsx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="artifact_type must be pdf, csv, or xlsx",
        )

    artifact_id = str(uuid.uuid4())
    ext = request.artifact_type
    storage_dir = os.path.join(
        settings.storage_path, "artifacts", current_user.id, session_id
    )
    os.makedirs(storage_dir, exist_ok=True)
    file_path = os.path.join(storage_dir, f"{artifact_id}.{ext}")

    try:
        if ext == "pdf":
            _generate_pdf(request.content, file_path)
        elif ext == "csv":
            _generate_csv(request.content, file_path, request.columns)
        elif ext == "xlsx":
            _generate_xlsx(request.content, file_path, request.columns)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate artifact: {str(e)}",
        )

    artifact = Artifact(
        id=artifact_id,
        user_id=current_user.id,
        session_id=session_id,
        artifact_type=ext,
        display_name=request.display_name,
        file_path=file_path,
        artifact_metadata={"columns": request.columns},
    )
    db.add(artifact)
    db.commit()
    db.refresh(artifact)
    return artifact


@router.get("/artifacts/{artifact_id}/download")
def download_artifact(
    artifact_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    artifact = (
        db.query(Artifact)
        .filter(Artifact.id == artifact_id, Artifact.user_id == current_user.id)
        .first()
    )
    if not artifact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")

    if not artifact.file_path or not os.path.exists(artifact.file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact file not found")

    media_type_map = {
        "pdf": "application/pdf",
        "csv": "text/csv",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    }
    media_type = media_type_map.get(artifact.artifact_type, "application/octet-stream")

    return FileResponse(
        path=artifact.file_path,
        media_type=media_type,
        filename=f"{artifact.display_name}.{artifact.artifact_type}",
    )
