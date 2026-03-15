import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.users import User
from app.models.platform_settings import PlatformSetting

router = APIRouter(prefix="/admin", tags=["admin"])

EMBEDDING_MODEL_KEY = "active_embedding_model"

AVAILABLE_EMBEDDING_MODELS = [
    {
        "id": "sentence-transformers/all-MiniLM-L6-v2",
        "name": "MiniLM-L6-v2 (Local, Free)",
        "provider": "sentence-transformers",
    },
    {
        "id": "azure-text-embedding-3-small",
        "name": "Azure OpenAI text-embedding-3-small",
        "provider": "azure_openai",
    },
    {
        "id": "azure-text-embedding-3-large",
        "name": "Azure OpenAI text-embedding-3-large",
        "provider": "azure_openai",
    },
]


def _require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


class EmbeddingModelUpdate(BaseModel):
    model_id: str


class PlatformSettingsResponse(BaseModel):
    active_embedding_model: str
    available_embedding_models: list


@router.get("/settings", response_model=PlatformSettingsResponse)
def get_platform_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_admin),
):
    setting = db.query(PlatformSetting).filter(PlatformSetting.key == EMBEDDING_MODEL_KEY).first()
    active_model = setting.value if setting else "sentence-transformers/all-MiniLM-L6-v2"

    return PlatformSettingsResponse(
        active_embedding_model=active_model,
        available_embedding_models=AVAILABLE_EMBEDDING_MODELS,
    )


@router.put("/settings/embedding-model")
def update_embedding_model(
    request: EmbeddingModelUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_admin),
):
    valid_ids = [m["id"] for m in AVAILABLE_EMBEDDING_MODELS]
    if request.model_id not in valid_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid model. Must be one of: {valid_ids}",
        )

    setting = db.query(PlatformSetting).filter(PlatformSetting.key == EMBEDDING_MODEL_KEY).first()
    if setting:
        setting.value = request.model_id
        setting.updated_by = current_user.id
        setting.updated_at = datetime.utcnow()
    else:
        setting = PlatformSetting(
            id=str(uuid.uuid4()),
            key=EMBEDDING_MODEL_KEY,
            value=request.model_id,
            updated_by=current_user.id,
        )
        db.add(setting)

    db.commit()

    # Reset cached embedding model so next call picks up the new one
    from app.services.embeddings import reset_model
    reset_model()

    return {"message": "Embedding model updated", "active_embedding_model": request.model_id}
