from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    app_env: str = "local"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    frontend_url: str = "http://localhost:3000"

    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "deep_research"
    postgres_user: str = "app_user"
    postgres_password: str = "app_password"

    chroma_host: str = "chroma"
    chroma_port: int = 8000
    chroma_persist_dir: str = "/data/chroma"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    azure_openai_api_key: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_api_version: str = "2024-12-01-preview"
    azure_openai_gpt_deployment: str = "gpt-4o"
    azure_openai_embedding_deployment_small: str = "text-embedding-3-small"
    azure_openai_embedding_deployment_large: str = "text-embedding-3-large"

    jwt_secret: str = "change_me_to_a_secure_random_string"
    jwt_expire_minutes: int = 1440

    max_files_and_urls_per_session: int = 10
    max_upload_mb: int = 50
    max_pasted_text_chars: int = 50000
    max_skill_zip_mb: int = 20
    max_code_exec_seconds: int = 20
    enable_code_execution: bool = True
    enable_skills: bool = True

    seed_admin_user: bool = True
    seed_admin_username: str = "admin"
    seed_admin_password: str = "admin$123"

    storage_path: str = "/storage"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
