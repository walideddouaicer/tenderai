from __future__ import annotations

import asyncio

from sentence_transformers import SentenceTransformer

MODEL_NAME = "intfloat/multilingual-e5-base"

_model: SentenceTransformer | None = None


def get_embedder() -> SentenceTransformer:
    """Return the loaded model, downloading and caching on first call (~560 MB)."""
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


async def embed_passages(texts: list[str]) -> list[list[float]]:
    """
    Embed document passages for indexing.
    Prepends 'passage: ' per intfloat/e5 specification.
    Runs encode() in a thread pool — it is CPU-bound and blocking.
    """
    prefixed = [f"passage: {t}" for t in texts]
    model = get_embedder()
    vecs = await asyncio.to_thread(model.encode, prefixed, convert_to_numpy=True)
    return vecs.tolist()


async def embed_query(text: str) -> list[float]:
    """
    Embed a search query for retrieval.
    Prepends 'query: ' per intfloat/e5 specification.
    """
    model = get_embedder()
    vecs = await asyncio.to_thread(model.encode, [f"query: {text}"], convert_to_numpy=True)
    return vecs.tolist()[0]
