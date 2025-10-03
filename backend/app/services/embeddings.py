from __future__ import annotations

from typing import List
from loguru import logger

from sentence_transformers import SentenceTransformer
from ..config import settings

_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
        _model = SentenceTransformer(settings.EMBEDDING_MODEL)
    return _model


def embed_texts(texts: List[str]) -> List[List[float]]:
    model = get_model()
    vectors = model.encode(texts, normalize_embeddings=True).tolist()
    return vectors



