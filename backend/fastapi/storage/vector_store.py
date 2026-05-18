from __future__ import annotations

import abc
from dataclasses import dataclass, field


@dataclass
class Chunk:
    id: str
    text: str
    tender_id: str
    page_number: int
    section_header: str
    document_type: str
    language: str
    ocr_fallback: bool = False
    embedding: list[float] = field(default_factory=list)


@dataclass
class SearchResult:
    chunk: Chunk
    score: float


class VectorStore(abc.ABC):
    """
    Abstract interface for all vector storage backends.
    Application code must only import this class — never chromadb or pinecone directly.
    """

    @abc.abstractmethod
    def add_chunks(self, chunks: list[Chunk]) -> None:
        """Embed and index a list of chunks."""

    @abc.abstractmethod
    def search(self, tender_id: str, query_embedding: list[float], top_k: int = 5) -> list[SearchResult]:
        """Return the top_k most similar chunks for the given tender."""

    @abc.abstractmethod
    def delete_tender(self, tender_id: str) -> None:
        """Remove all chunks associated with a tender."""


class ChromaVectorStore(VectorStore):
    """ChromaDB-backed implementation. Only this class may import chromadb."""

    def __init__(self, host: str = "localhost", port: int = 8002) -> None:
        import chromadb  # noqa: PLC0415 — intentionally isolated here

        self._client = chromadb.HttpClient(host=host, port=port)
        self._collection = self._client.get_or_create_collection(
            name="tender_chunks",
            metadata={"hnsw:space": "cosine"},
        )

    def add_chunks(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return
        self._collection.add(
            ids=[c.id for c in chunks],
            embeddings=[c.embedding for c in chunks],
            documents=[c.text for c in chunks],
            metadatas=[
                {
                    "tender_id": c.tender_id,
                    "page_number": c.page_number,
                    "section_header": c.section_header,
                    "document_type": c.document_type,
                    "language": c.language,
                    "ocr_fallback": c.ocr_fallback,
                }
                for c in chunks
            ],
        )

    def search(self, tender_id: str, query_embedding: list[float], top_k: int = 5) -> list[SearchResult]:
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where={"tender_id": tender_id},
        )
        output: list[SearchResult] = []
        for i, doc_id in enumerate(results["ids"][0]):
            meta = results["metadatas"][0][i]
            chunk = Chunk(
                id=doc_id,
                text=results["documents"][0][i],
                tender_id=meta["tender_id"],
                page_number=meta["page_number"],
                section_header=meta["section_header"],
                document_type=meta["document_type"],
                language=meta["language"],
                ocr_fallback=meta["ocr_fallback"],
            )
            score = results["distances"][0][i]
            output.append(SearchResult(chunk=chunk, score=score))
        return output

    def delete_tender(self, tender_id: str) -> None:
        self._collection.delete(where={"tender_id": tender_id})


def get_vector_store() -> VectorStore:
    from decouple import config  # noqa: PLC0415

    backend = config("VECTOR_STORE_BACKEND", default="chroma")
    if backend == "chroma":
        return ChromaVectorStore(
            host=config("CHROMADB_HOST", default="localhost"),
            port=config("CHROMADB_PORT", default=8002, cast=int),
        )
    raise ValueError(f"Unknown VECTOR_STORE_BACKEND: {backend!r}")
