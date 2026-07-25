"""
Domain knowledge service.

Purpose:
Public entry point for the Domain Agent's RAG pipeline -- ingest domain
documents (PDF/DOCX/TXT/MD) into the vector store, and retrieve the most
relevant chunks for a given query.

Why this is a standalone service and not agent-internal:
Ingestion is a general concern (a CLI script populates the knowledge base
independently of any single agent run), even though DomainAgent is its
only consumer today.

Reliability contract:
retrieve() NEVER raises. A missing Chroma directory, an empty collection,
or a model load failure all just mean "no domain knowledge available yet"
-- it logs a warning and returns []. DomainAgent's reliability ladder
depends on this: retrieval failure must never be the reason a Domain
Agent run fails.
"""

from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services.rag.chunking import chunk_text
from app.services.rag.embedding import domain_embedder
from app.services.rag.loaders import SUPPORTED_EXTENSIONS, load_text_from_file
from app.services.rag.vector_store import chroma_domain_vector_store
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DomainKnowledgeService:
    """
    Ingests domain knowledge files and retrieves relevant chunks for a query.
    """

    def ingest_path(self, path: str | Path | None = None) -> dict[str, Any]:
        """
        Ingest one file, or every supported file under a directory
        (recursively), into the vector store.

        Never raises for a single bad file -- that file is counted in
        files_skipped and ingestion continues with the rest.
        """

        target = Path(path) if path else Path(settings.DOMAIN_KNOWLEDGE_BASE_DIR)

        if not target.exists():
            logger.warning("Domain knowledge path does not exist: %s", target)
            return {"files_ingested": 0, "chunks_created": 0, "files_skipped": 0}

        if target.is_file():
            files = [target]
        else:
            files = sorted(
                file for file in target.rglob("*")
                if file.is_file() and file.suffix.lower() in SUPPORTED_EXTENSIONS
            )

        files_ingested = 0
        chunks_created = 0
        files_skipped = 0

        for file_path in files:
            try:
                text = load_text_from_file(file_path)
                chunks = chunk_text(text, source_document=file_path.name)

                if not chunks:
                    logger.warning("No extractable text in domain knowledge file: %s", file_path)
                    files_skipped += 1
                    continue

                embeddings = domain_embedder.embed_texts([chunk["text"] for chunk in chunks])
                chroma_domain_vector_store.upsert(chunks, embeddings)

                files_ingested += 1
                chunks_created += len(chunks)

            except Exception as error:
                logger.warning("Skipping domain knowledge file %s: %s", file_path, error)
                files_skipped += 1

        return {
            "files_ingested": files_ingested,
            "chunks_created": chunks_created,
            "files_skipped": files_skipped,
        }

    def retrieve(self, query_text: str, top_k: int | None = None) -> list[dict]:
        """
        Retrieve the most relevant domain knowledge chunks for a query.

        Never raises. Returns [] if the vector store is empty/missing, the
        embedding model fails to load, or any other retrieval error occurs.
        """

        if not query_text or not query_text.strip():
            return []

        try:
            embedding = domain_embedder.embed_texts([query_text])[0]
            return chroma_domain_vector_store.query(
                embedding=embedding,
                top_k=top_k or settings.DOMAIN_TOP_K,
            )

        except Exception as error:
            logger.warning("Domain knowledge retrieval failed, returning no chunks: %s", error)
            return []


domain_knowledge_service = DomainKnowledgeService()
