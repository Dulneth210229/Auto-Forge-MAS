"""
Domain knowledge vector store.

Purpose:
Wrap ChromaDB so the rest of the Domain Agent RAG pipeline never touches
the ChromaDB client API directly.

Why Chroma over MongoDB Atlas Vector Search:
langchain-mongodb is present in this project's environment, but Atlas
Vector Search requires a separately-configured Atlas Search index on a
real Atlas cluster -- extra infra for no capability gain at this project's
scale (a single local knowledge base). settings.CHROMA_PERSIST_DIR already
names Chroma explicitly, so this is the zero-new-infra path.
"""

from app.core.config import settings

COLLECTION_NAME = "domain_knowledge"


class ChromaDomainVectorStore:
    """
    Thin wrapper around one persistent ChromaDB collection.
    """

    def __init__(self):
        self._client = None
        self._collection = None

    def _get_collection(self):
        if self._collection is None:
            import chromadb

            self._client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
            self._collection = self._client.get_or_create_collection(name=COLLECTION_NAME)

        return self._collection

    def upsert(self, chunks: list[dict], embeddings: list[list[float]]) -> None:
        """
        Insert or overwrite vectors for the given chunks.

        chunks: [{"chunk_id", "source_document", "text"}, ...]
        embeddings: parallel list of embedding vectors.
        """

        if not chunks:
            return

        collection = self._get_collection()

        collection.upsert(
            ids=[chunk["chunk_id"] for chunk in chunks],
            embeddings=embeddings,
            documents=[chunk["text"] for chunk in chunks],
            metadatas=[{"source_document": chunk["source_document"]} for chunk in chunks],
        )

    def query(self, embedding: list[float], top_k: int) -> list[dict]:
        """
        Return the top_k most similar chunks to the given query embedding.

        Returns: [{"chunk_id", "source_document", "text", "distance"}, ...]
        Empty collection or any query error -> propagates to the caller,
        which is expected to catch it (domain_knowledge_service.retrieve
        never raises).
        """

        collection = self._get_collection()

        if collection.count() == 0:
            return []

        result = collection.query(
            query_embeddings=[embedding],
            n_results=min(top_k, collection.count()),
        )

        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        chunks = []

        for index, chunk_id in enumerate(ids):
            metadata = metadatas[index] if index < len(metadatas) else {}
            chunks.append({
                "chunk_id": chunk_id,
                "source_document": (metadata or {}).get("source_document", "unknown"),
                "text": documents[index] if index < len(documents) else "",
                "distance": distances[index] if index < len(distances) else None,
            })

        return chunks


chroma_domain_vector_store = ChromaDomainVectorStore()
