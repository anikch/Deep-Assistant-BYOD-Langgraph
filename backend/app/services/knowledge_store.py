import logging
from typing import List, Tuple, Dict, Any, Optional

import chromadb

from app.core.config import settings
from app.services.embeddings import get_embeddings, get_embedding

logger = logging.getLogger(__name__)


class KnowledgeStore:
    def __init__(self):
        self._client = None

    def _get_client(self) -> chromadb.HttpClient:
        if self._client is None:
            self._client = chromadb.HttpClient(
                host=settings.chroma_host,
                port=settings.chroma_port,
            )
        return self._client

    def _collection_name(self, session_id: str) -> str:
        # Chroma collection names must be valid identifiers
        safe_id = session_id.replace("-", "_")
        return f"session_{safe_id}"

    def _get_collection(self, session_id: str):
        client = self._get_client()
        name = self._collection_name(session_id)
        return client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_chunks(
        self,
        session_id: str,
        user_id: str,
        source_id: str,
        chunks: List[Tuple[str, int]],  # (text, chunk_index)
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """Add chunks to the session's Chroma collection."""
        if not chunks:
            return []

        collection = self._get_collection(session_id)
        texts = [c[0] for c in chunks]
        embeddings = get_embeddings(texts)

        ids = []
        metadatas = []
        for chunk_text, chunk_idx in chunks:
            doc_id = f"{source_id}_{chunk_idx}"
            ids.append(doc_id)
            meta = {
                "user_id": user_id,
                "session_id": session_id,
                "source_id": source_id,
                "chunk_index": chunk_idx,
            }
            if extra_metadata:
                meta.update(extra_metadata)
            metadatas.append(meta)

        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )
        logger.info(f"Added {len(ids)} chunks to session {session_id} collection")
        return ids

    def search(
        self,
        session_id: str,
        query: str,
        top_k: int = 5,
        source_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant chunks in a session's collection.
        NEVER cross-session retrieval - collection is session-scoped.
        """
        try:
            collection = self._get_collection(session_id)
            query_embedding = get_embedding(query)

            where = {"session_id": session_id}
            if source_ids:
                where["source_id"] = {"$in": source_ids}

            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, max(1, collection.count())),
                where=where,
                include=["documents", "metadatas", "distances"],
            )

            output = []
            if results and results.get("documents"):
                for i, doc in enumerate(results["documents"][0]):
                    output.append({
                        "text": doc,
                        "metadata": results["metadatas"][0][i],
                        "distance": results["distances"][0][i],
                    })
            return output
        except Exception as e:
            logger.error(f"Search failed for session {session_id}: {e}")
            return []

    def delete_source(self, session_id: str, source_id: str) -> None:
        """Delete all chunks for a specific source from the session collection."""
        try:
            collection = self._get_collection(session_id)
            collection.delete(where={"source_id": source_id})
            logger.info(f"Deleted source {source_id} chunks from session {session_id}")
        except Exception as e:
            logger.error(f"Failed to delete source {source_id}: {e}")

    def delete_session(self, session_id: str) -> None:
        """Delete the entire session collection."""
        try:
            client = self._get_client()
            name = self._collection_name(session_id)
            client.delete_collection(name)
            logger.info(f"Deleted collection for session {session_id}")
        except Exception as e:
            logger.error(f"Failed to delete session collection {session_id}: {e}")
