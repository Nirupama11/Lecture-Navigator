from __future__ import annotations

from typing import Any, Dict, List, Optional
from loguru import logger
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING
from datetime import datetime

from ..config import settings


class InMemoryStore:
    def __init__(self) -> None:
        self._videos: Dict[str, Dict[str, Any]] = {}
        self._segments: List[Dict[str, Any]] = []

    async def upsert_segments(self, video_id: str, title: str, segments: List[Dict[str, Any]], url: Optional[str] = None, is_local_file: bool = False) -> None:
        self._videos[video_id] = {
            "video_id": video_id, 
            "title": title, 
            "url": url,
            "created_at": datetime.now().isoformat(),
            "is_local_file": is_local_file
        }
        self._segments = [s for s in self._segments if s.get("video_id") != video_id]
        for s in segments:
            s["video_id"] = video_id
        self._segments.extend(segments)

    async def search(self, query_embedding: List[float], k: int, video_id: Optional[str]) -> List[Dict[str, Any]]:
        import numpy as np

        qe = np.array(query_embedding)
        results = []
        for s in self._segments:
            if video_id and s.get("video_id") != video_id:
                continue
            emb = np.array(s["embedding"]) if "embedding" in s else None
            if emb is None or emb.shape != qe.shape:
                continue
            denom = (np.linalg.norm(qe) * np.linalg.norm(emb)) or 1e-9
            score = float(np.dot(qe, emb) / denom)
            results.append({**s, "score": score})
        results.sort(key=lambda x: x.get("score", 0.0), reverse=True)
        return results[:k]

    async def list_segments(self, video_id: Optional[str], limit: int = 2000) -> List[Dict[str, Any]]:
        items = [s for s in self._segments if (not video_id or s.get("video_id") == video_id)]
        return items[:limit]

    async def get_videos(self) -> List[Dict[str, Any]]:
        return list(self._videos.values())


class MongoStore:
    def __init__(self) -> None:
        self.client = AsyncIOMotorClient(settings.MONGODB_URI)
        self.db = self.client[settings.MONGODB_DB]
        self.col = self.db[settings.MONGODB_COLLECTION]
        self.videos_col = self.db["videos"]

    async def ensure_indexes(self) -> None:
        await self.col.create_index([("video_id", ASCENDING)])
        await self.videos_col.create_index([("video_id", ASCENDING)], unique=True)

    async def upsert_segments(self, video_id: str, title: str, segments: List[Dict[str, Any]], url: Optional[str] = None, is_local_file: bool = False) -> None:
        await self.col.delete_many({"video_id": video_id})
        for s in segments:
            s["video_id"] = video_id
            s["title"] = title
        if segments:
            await self.col.insert_many(segments)
        
        # Store video metadata
        video_info = {
            "video_id": video_id,
            "title": title,
            "url": url,
            "created_at": datetime.now().isoformat(),
            "is_local_file": is_local_file
        }
        await self.videos_col.replace_one({"video_id": video_id}, video_info, upsert=True)

    async def search(self, query_embedding: List[float], k: int, video_id: Optional[str]) -> List[Dict[str, Any]]:
        filter_query: Dict[str, Any] = {}
        if video_id:
            filter_query["video_id"] = video_id
        try:
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": "vector_index",
                        "path": "embedding",
                        "queryVector": query_embedding,
                        "numCandidates": max(k * 10, 100),
                        "limit": k,
                    }
                },
                {"$addFields": {"score": {"$meta": "vectorSearchScore"}}},
            ]
            if filter_query:
                pipeline.insert(0, {"$match": filter_query})
            cursor = self.col.aggregate(pipeline)
            return [doc async for doc in cursor]
        except Exception as e:
            logger.warning(f"VectorSearch not available, falling back to cosine in Mongo: {e}")
            import numpy as np
            qe = np.array(query_embedding)
            docs = [d async for d in self.col.find(filter_query)]
            results: List[Dict[str, Any]] = []
            for d in docs:
                emb = d.get("embedding")
                if not emb:
                    continue
                emb_arr = np.array(emb)
                denom = (np.linalg.norm(qe) * np.linalg.norm(emb_arr)) or 1e-9
                score = float(np.dot(qe, emb_arr) / denom)
                d["score"] = score
                results.append(d)
            results.sort(key=lambda x: x.get("score", 0.0), reverse=True)
            return results[:k]

    async def list_segments(self, video_id: Optional[str], limit: int = 2000) -> List[Dict[str, Any]]:
        q: Dict[str, Any] = {}
        if video_id:
            q["video_id"] = video_id
        cursor = self.col.find(q, projection={"embedding": 0}).limit(limit)
        return [doc async for doc in cursor]

    async def get_videos(self) -> List[Dict[str, Any]]:
        cursor = self.videos_col.find({}).sort("created_at", -1)
        return [doc async for doc in cursor]


async def get_store() -> Any:
    try:
        store = MongoStore()
        await store.ensure_indexes()
        logger.info("Using MongoStore")
        return store
    except Exception as e:
        logger.warning(f"Mongo unavailable, using InMemoryStore: {e}")
        return InMemoryStore()
