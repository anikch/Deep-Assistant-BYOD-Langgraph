import logging
from typing import List

logger = logging.getLogger(__name__)

_model = None
_current_model_id = None


def _get_active_model_id() -> str:
    """Read the active embedding model from platform_settings table."""
    try:
        from app.db.session import SessionLocal
        from app.models.platform_settings import PlatformSetting

        db = SessionLocal()
        try:
            setting = db.query(PlatformSetting).filter(
                PlatformSetting.key == "active_embedding_model"
            ).first()
            return setting.value if setting else "sentence-transformers/all-MiniLM-L6-v2"
        finally:
            db.close()
    except Exception:
        return "sentence-transformers/all-MiniLM-L6-v2"


def reset_model():
    """Reset cached model so next call picks up the new configuration."""
    global _model, _current_model_id
    _model = None
    _current_model_id = None


def _get_model():
    global _model, _current_model_id
    model_id = _get_active_model_id()

    # If model changed, reset cache
    if _current_model_id != model_id:
        _model = None

    if _model is not None:
        return _model, model_id

    _current_model_id = model_id

    if model_id == "sentence-transformers/all-MiniLM-L6-v2":
        from sentence_transformers import SentenceTransformer
        logger.info("Loading sentence-transformers model: all-MiniLM-L6-v2")
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("Model loaded successfully")
    elif model_id in ("azure-text-embedding-3-small", "azure-text-embedding-3-large"):
        from app.core.config import settings
        if not settings.azure_openai_api_key:
            raise ValueError("AZURE_OPENAI_API_KEY is not configured for Azure embedding model")
        # Use a marker object; actual calls go through the Azure API
        _model = "azure_openai"
        logger.info(f"Using Azure OpenAI embedding model: {model_id}")
    else:
        raise ValueError(f"Unknown embedding model: {model_id}")

    return _model, model_id


def _azure_embeddings(texts: List[str], model_id: str) -> List[List[float]]:
    """Generate embeddings via Azure OpenAI API."""
    from openai import AzureOpenAI
    from app.core.config import settings

    deployment = (
        settings.azure_openai_embedding_deployment_small
        if model_id == "azure-text-embedding-3-small"
        else settings.azure_openai_embedding_deployment_large
    )

    client = AzureOpenAI(
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
        azure_endpoint=settings.azure_openai_endpoint,
    )

    response = client.embeddings.create(input=texts, model=deployment)
    return [item.embedding for item in response.data]


def get_embeddings(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for a list of texts."""
    if not texts:
        return []

    model, model_id = _get_model()

    if model == "azure_openai":
        return _azure_embeddings(texts, model_id)

    # sentence-transformers path
    embeddings = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
    return embeddings.tolist()


def get_embedding(text: str) -> List[float]:
    """Generate embedding for a single text."""
    results = get_embeddings([text])
    return results[0] if results else []
