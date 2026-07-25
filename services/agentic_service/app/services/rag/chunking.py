"""
Domain knowledge chunking.

Purpose:
Split one document's plain text into overlapping chunks small enough to
embed meaningfully, each tagged with a deterministic chunk_id and its
source document name.

Why deterministic chunk_id:
Re-running ingestion on the same file must upsert the same vector IDs
instead of duplicating them in the vector store.
"""

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings


def chunk_text(text: str, source_document: str) -> list[dict]:
    """
    Split text into chunks.

    Returns a list of:
        {"chunk_id": "<source_document>#<index>", "source_document": ..., "text": ...}
    """

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.DOMAIN_CHUNK_SIZE,
        chunk_overlap=settings.DOMAIN_CHUNK_OVERLAP,
    )

    pieces = splitter.split_text(text)

    return [
        {
            "chunk_id": f"{source_document}#{index}",
            "source_document": source_document,
            "text": piece,
        }
        for index, piece in enumerate(pieces)
        if piece.strip()
    ]
