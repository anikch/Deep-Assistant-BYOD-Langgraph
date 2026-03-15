import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


def run_migrations():
    """Run Alembic migrations on startup."""
    try:
        from alembic.config import Config
        from alembic import command
        import os

        alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
        alembic_cfg.set_main_option("script_location", os.path.join(os.path.dirname(__file__), "..", "alembic"))
        command.upgrade(alembic_cfg, "head")
        logger.info("Alembic migrations applied successfully")
    except Exception as e:
        logger.error(f"Failed to run migrations: {e}", exc_info=True)
        # Try direct table creation as fallback
        try:
            from app.db.session import engine, Base
            import app.models  # noqa: ensure models are imported
            Base.metadata.create_all(bind=engine)
            logger.info("Tables created via SQLAlchemy metadata")
        except Exception as e2:
            logger.error(f"Fallback table creation also failed: {e2}")


def seed_data():
    """Seed initial data."""
    try:
        from app.db.session import SessionLocal
        from app.core.seed import seed_admin_user

        db = SessionLocal()
        try:
            seed_admin_user(db)
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Failed to seed data: {e}", exc_info=True)


def ensure_storage_dirs():
    """Ensure required storage directories exist."""
    dirs = [
        settings.storage_path,
        os.path.join(settings.storage_path, "uploads"),
        os.path.join(settings.storage_path, "skills"),
        os.path.join(settings.storage_path, "artifacts"),
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    logger.info("Starting up Assistant PoC backend...")
    ensure_storage_dirs()
    run_migrations()
    seed_data()
    logger.info("Startup complete")
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="Assistant PoC - Deep Research Agent",
    description="Multi-user, session-isolated NotebookLM-lite + agentic research chat",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
from app.api import auth, sessions, sources, chat, skills, artifacts, admin

app.include_router(auth.router)
app.include_router(sessions.router)
app.include_router(sources.router)
app.include_router(chat.router)
app.include_router(skills.router)
app.include_router(artifacts.router)
app.include_router(admin.router)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "Assistant PoC Backend"}


@app.get("/")
def root():
    return {"message": "Assistant PoC API", "docs": "/docs"}
