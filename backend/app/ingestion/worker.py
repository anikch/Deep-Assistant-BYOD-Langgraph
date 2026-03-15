import logging
import uuid
from datetime import datetime

from app.db.session import SessionLocal
from app.models.sources import Source, IngestStatus
from app.models.source_chunks_metadata import SourceChunkMetadata
from app.ingestion.extractor import extract_text
from app.ingestion.chunker import chunk_text_with_overlap
from app.services.knowledge_store import KnowledgeStore

logger = logging.getLogger(__name__)


def process_source(source_id: str) -> None:
    """
    Background task to ingest a source:
    1. Extract text
    2. Chunk
    3. Embed + store in Chroma
    4. Record chunk metadata in PostgreSQL
    """
    db = SessionLocal()
    try:
        source = db.query(Source).filter(Source.id == source_id).first()
        if not source:
            logger.error(f"Source {source_id} not found")
            return

        source.ingest_status = IngestStatus.processing
        source.updated_at = datetime.utcnow()
        db.commit()

        # Extract text
        text = extract_text(
            source_type=source.source_type.value if hasattr(source.source_type, "value") else source.source_type,
            file_path=source.local_path,
            url=source.source_url,
        )

        if not text or not text.strip():
            logger.warning(f"No text extracted from source {source_id}")
            source.ingest_status = IngestStatus.failed
            source.updated_at = datetime.utcnow()
            db.commit()
            return

        # Chunk text
        chunks = chunk_text_with_overlap(text, chunk_size=1000, chunk_overlap=200)
        if not chunks:
            source.ingest_status = IngestStatus.failed
            source.updated_at = datetime.utcnow()
            db.commit()
            return

        # Store in Chroma
        ks = KnowledgeStore()
        extra_meta = {
            "source_type": source.source_type.value if hasattr(source.source_type, "value") else source.source_type,
            "source_name": source.display_name,
            "created_at": source.created_at.isoformat() if source.created_at else "",
        }
        vector_ids = ks.add_chunks(
            session_id=source.session_id,
            user_id=source.user_id,
            source_id=source_id,
            chunks=chunks,
            extra_metadata=extra_meta,
        )

        # Store chunk metadata in PostgreSQL
        for i, (chunk_text, chunk_idx) in enumerate(chunks):
            chunk_meta = SourceChunkMetadata(
                id=str(uuid.uuid4()),
                source_id=source_id,
                user_id=source.user_id,
                session_id=source.session_id,
                chunk_index=chunk_idx,
                vector_ref=vector_ids[i] if i < len(vector_ids) else None,
                chunk_metadata={
                    "text_preview": chunk_text[:200],
                    "char_count": len(chunk_text),
                },
            )
            db.add(chunk_meta)

        source.ingest_status = IngestStatus.complete
        source.updated_at = datetime.utcnow()
        db.commit()
        logger.info(f"Source {source_id} ingested successfully with {len(chunks)} chunks")

    except Exception as e:
        logger.error(f"Failed to process source {source_id}: {e}", exc_info=True)
        try:
            source = db.query(Source).filter(Source.id == source_id).first()
            if source:
                source.ingest_status = IngestStatus.failed
                source.updated_at = datetime.utcnow()
                db.commit()
        except Exception:
            pass
    finally:
        db.close()
