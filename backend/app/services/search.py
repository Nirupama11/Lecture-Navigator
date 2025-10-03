from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from loguru import logger
from functools import lru_cache

from .embeddings import embed_texts
from .db import get_store


# simple in-process cache keyed by (video_id, query) - note: lru_cache here only caches keys,
# actual cached values would require a sync store. Kept for compatibility with earlier design.
@lru_cache(maxsize=512)
def _cache_key(video_id: Optional[str], query: str) -> Tuple[Optional[str], str]:
    return (video_id, query)


async def index_segments(video_id: str, title: str, segments: List[Dict[str, Any]], url: Optional[str] = None, is_local_file: bool = False) -> None:
    """
    Compute embeddings for each segment and upsert into vector store.
    Each stored doc will include: video_id, title, start_time, end_time, text, embedding, metadata
    """
    if not segments:
        logger.info(f"No segments to index for {video_id}")
        return

    texts = [s["text"] for s in segments]
    vectors = embed_texts(texts)
    for s, v in zip(segments, vectors):
        s["embedding"] = v
        s["video_id"] = video_id
        s["title"] = title
        # optionally precompute snippet
        s["snippet"] = s["text"][:300]

    store = await get_store()
    await store.upsert_segments(video_id, title, segments, url, is_local_file)
    logger.info(f"Indexed {len(segments)} segments for video {video_id}")


async def get_video_history() -> List[Dict[str, Any]]:
    """Get list of all processed videos"""
    store = await get_store()
    return await store.get_videos()


async def _keyword_fallback(query: str, k: int, video_id: Optional[str]) -> List[Dict[str, Any]]:
    """
    Very small fallback that scans stored segments and ranks by simple term frequency.
    """
    store = await get_store()
    docs = await store.list_segments(video_id, limit=5000)
    q = query.lower()
    scored: List[Tuple[float, Dict[str, Any]]] = []
    q_tokens = [tok for tok in q.split() if tok]
    for d in docs:
        text = (d.get("text") or "").lower()
        score = sum(text.count(tok) for tok in q_tokens)
        if score > 0:
            d2 = dict(d)
            d2["score"] = float(score)
            scored.append((float(score), d2))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [d for _, d in scored[:k]]


async def semantic_search(query: str, k: int = 3, video_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Perform vector search using the embedding of the query.
    Returns top-k documents (each doc is a dict containing at least: video_id, start_time, end_time, text, score).
    If the vector scores are weak, attempt keyword fallback and merge results.
    """
    # Obtain query vector
    qv = embed_texts([query])[0]

    store = await get_store()
    # Ask for a larger candidate set to allow reranking/merging
    candidates = await store.search(qv, k * 4, video_id)
    if not candidates:
        # fallback immediately to keyword search
        fb = await _keyword_fallback(query, k, video_id)
        return fb

    # sort primarily by score, secondarily by end_time (prefer later occurrences for context)
    candidates.sort(key=lambda x: (x.get("score", 0.0), x.get("end_time", 0.0)), reverse=True)
    topk = candidates[:k]

    # If the top score is weak, attempt keyword fallback and merge
    top_score = topk[0].get("score", 0.0) if topk else 0.0
    if top_score < 0.2:
        fb = await _keyword_fallback(query, k, video_id)

        def key(d):
            return (d.get("video_id"), d.get("start_time"), d.get("end_time"))

        seen = set()
        merged: List[Dict[str, Any]] = []
        for d in (topk + fb):
            kx = key(d)
            if kx in seen:
                continue
            seen.add(kx)
            merged.append(d)
        merged.sort(key=lambda x: x.get("score", 0.0), reverse=True)
        return merged[:k]

    return topk
