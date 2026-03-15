import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from app.core.config import settings

logger = logging.getLogger(__name__)

LLM_PROVIDER_GEMINI = "gemini"
LLM_PROVIDER_AZURE_OPENAI = "azure_openai"

AVAILABLE_LLM_MODELS = [
    {"id": LLM_PROVIDER_GEMINI, "name": f"Google Gemini ({settings.gemini_model})"},
    {"id": LLM_PROVIDER_AZURE_OPENAI, "name": f"Azure OpenAI GPT ({settings.azure_openai_gpt_deployment})"},
]


def get_llm(provider: str = LLM_PROVIDER_GEMINI):
    """Return a LangChain chat model for the requested provider."""
    if provider == LLM_PROVIDER_AZURE_OPENAI:
        return _get_azure_openai_llm()
    return _get_gemini_llm()


def _get_gemini_llm():
    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.gemini_api_key,
        temperature=0.3,
        convert_system_message_to_human=True,
    )


def _get_azure_openai_llm():
    from langchain_openai import AzureChatOpenAI

    if not settings.azure_openai_api_key:
        raise ValueError("AZURE_OPENAI_API_KEY is not configured")

    return AzureChatOpenAI(
        azure_deployment=settings.azure_openai_gpt_deployment,
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
        temperature=0.3,
    )
