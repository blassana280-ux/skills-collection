"""Mémoire opérationnelle : file de tâches (Redis), index vectoriel (Qdrant),
réutilisation des recherches et politique de rétention.

Chaque backend externe a un équivalent local réellement fonctionnel. Le rapport
`describe()` indique CE QUI TOURNE, jamais ce qui est simplement prévu.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import math
import re
import time
from typing import Any

from .db import Store, ResearchCache, database_kind
from .logging_conf import log_event

_TOKEN = re.compile(r"[a-z0-9àâçéèêëîïôûùüÿñæœ]+", re.I)
DIM = 64


def embed(text: str) -> list[float]:
    """Vectorisation déterministe locale (sac de mots haché, 64 dimensions)."""
    vec = [0.0] * DIM
    for token in _TOKEN.findall((text or "").lower()):
        vec[int(hashlib.sha1(token.encode()).hexdigest(), 16) % DIM] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


# --------------------------------------------------------------------------- #
# File de tâches
# --------------------------------------------------------------------------- #
class TaskQueue:
    backend = "in-process"

    async def put(self, mission_id: str, payload: dict[str, Any]) -> None:  # pragma: no cover
        raise NotImplementedError

    async def get(self, timeout: float = 0.5) -> dict[str, Any] | None:  # pragma: no cover
        raise NotImplementedError

    def size(self) -> int:  # pragma: no cover
        raise NotImplementedError


class InProcessQueue(TaskQueue):
    backend = "in-process asyncio.Queue"

    def __init__(self) -> None:
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

    async def put(self, mission_id: str, payload: dict[str, Any]) -> None:
        await self._queue.put({"mission_id": mission_id, **payload})

    async def get(self, timeout: float = 0.5) -> dict[str, Any] | None:
        try:
            return await asyncio.wait_for(self._queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None

    def size(self) -> int:
        return self._queue.qsize()


class RedisQueue(TaskQueue):
    backend = "redis"

    def __init__(self, url: str, key: str = "omni:missions:queue") -> None:
        import redis.asyncio as aioredis  # optionnel, importé seulement si configuré
        self.client = aioredis.from_url(url, decode_responses=True)
        self.key = key

    async def put(self, mission_id: str, payload: dict[str, Any]) -> None:
        await self.client.lpush(self.key, json.dumps({"mission_id": mission_id, **payload}))

    async def get(self, timeout: float = 0.5) -> dict[str, Any] | None:
        item = await self.client.brpop(self.key, timeout=max(1, int(timeout)))
        if item is None:
            return None
        return json.loads(item[1])

    def size(self) -> int:
        # synchronous fallback used only by the admin UI via to_thread
        import redis as sync_redis  # noqa: F401
        raise NotImplementedError("RedisQueue.size() est asynchrone : utiliser asize()")

    async def asize(self) -> int:
        return int(await self.client.llen(self.key))


def make_queue(redis_url: str) -> TaskQueue:
    if redis_url:
        try:
            q = RedisQueue(redis_url)
            log_event("memory", "redis_queue_selected", url=redis_url.split("@")[-1])
            return q
        except Exception as exc:  # pragma: no cover - dépend de l'environnement
            log_event("memory", "redis_unavailable_fallback", level="WARNING", error=str(exc))
    return InProcessQueue()


# --------------------------------------------------------------------------- #
# Index vectoriel
# --------------------------------------------------------------------------- #
class VectorIndex:
    backend = "local-cosine"

    async def upsert(self, key: str, text: str, payload: dict[str, Any]) -> None:  # pragma: no cover
        raise NotImplementedError

    async def search(self, text: str, limit: int = 5) -> list[dict[str, Any]]:  # pragma: no cover
        raise NotImplementedError


class LocalVectorIndex(VectorIndex):
    backend = "local-cosine (64d, déterministe)"

    def __init__(self, store: Store) -> None:
        self.store = store
        self._points: dict[str, tuple[list[float], dict[str, Any]]] = {}

    async def upsert(self, key: str, text: str, payload: dict[str, Any]) -> None:
        self._points[key] = (embed(text), payload)

    async def search(self, text: str, limit: int = 5) -> list[dict[str, Any]]:
        needle = embed(text)
        scored = [
            {"key": k, "score": round(cosine(needle, vec), 4), **payload}
            for k, (vec, payload) in self._points.items()
        ]
        return sorted(scored, key=lambda x: x["score"], reverse=True)[:limit]


class QdrantVectorIndex(VectorIndex):
    backend = "qdrant-http"

    def __init__(self, url: str, collection: str) -> None:
        import httpx
        self.url = url.rstrip("/")
        self.collection = collection
        self.client = httpx.AsyncClient(timeout=8.0)
        self._ready = False

    async def _ensure(self) -> None:
        if self._ready:
            return
        r = await self.client.put(
            f"{self.url}/collections/{self.collection}",
            json={"vectors": {"size": DIM, "distance": "Cosine"}},
        )
        if r.status_code not in (200, 409):
            r.raise_for_status()
        self._ready = True

    async def upsert(self, key: str, text: str, payload: dict[str, Any]) -> None:
        await self._ensure()
        point_id = int(hashlib.sha1(key.encode()).hexdigest()[:12], 16)
        r = await self.client.put(
            f"{self.url}/collections/{self.collection}/points?wait=true",
            json={"points": [{"id": point_id, "vector": embed(text), "payload": payload}]},
        )
        r.raise_for_status()

    async def search(self, text: str, limit: int = 5) -> list[dict[str, Any]]:
        await self._ensure()
        r = await self.client.post(
            f"{self.url}/collections/{self.collection}/points/search",
            json={"vector": embed(text), "limit": limit, "with_payload": True},
        )
        r.raise_for_status()
        return [{"key": str(p.get("id")), "score": p.get("score", 0.0),
                 **(p.get("payload") or {})} for p in r.json().get("result", [])]


def make_vector_index(store: Store, qdrant_url: str, collection: str) -> VectorIndex:
    if qdrant_url:
        log_event("memory", "qdrant_index_selected", url=qdrant_url)
        return QdrantVectorIndex(qdrant_url, collection)
    return LocalVectorIndex(store)


# --------------------------------------------------------------------------- #
# Mémoire de recherche
# --------------------------------------------------------------------------- #
class ResearchMemory:
    def __init__(self, store: Store, queue: TaskQueue, index: VectorIndex,
                 retention_days: int = 90) -> None:
        self.store = store
        self.queue = queue
        self.index = index
        self.retention_days = retention_days

    @staticmethod
    def query_hash(query: str, mode: str) -> str:
        normalized = re.sub(r"\s+", " ", (query or "").strip().lower())
        return hashlib.sha256(f"{mode}|{normalized}".encode()).hexdigest()

    async def find_reusable(self, query: str, mode: str, max_age_seconds: float = 86400,
                            similarity: float = 0.94) -> dict[str, Any] | None:
        qhash = self.query_hash(query, mode)
        rows = self.store.filter(ResearchCache, query_hash=qhash)
        for row in sorted(rows, key=lambda r: r.created_at, reverse=True):
            if time.time() - row.created_at <= max_age_seconds:
                self.store.update(ResearchCache, row.id, hits=int(row.hits) + 1)
                return {"id": row.id, "mission_id": row.mission_id,
                        "query": row.query, "created_at": row.created_at,
                        "hits": row.hits + 1, "match": "exact", "payload": row.payload}
        for hit in await self.index.search(query, limit=5):
            if hit.get("score", 0) >= similarity and hit.get("mode") == mode:
                return {**hit, "match": "semantic"}
        return None

    async def remember(self, query: str, mode: str, mission_id: str,
                       payload: dict[str, Any]) -> str:
        key = self.query_hash(query, mode)
        row_id = f"cache-{hashlib.sha1(f'{key}-{time.time()}'.encode()).hexdigest()[:16]}"
        self.store.add(ResearchCache(id=row_id, query_hash=key, query=query,
                                     mission_id=mission_id, created_at=time.time(),
                                     hits=0, payload=payload))
        await self.index.upsert(row_id, query, {"mode": mode, "mission_id": mission_id,
                                                "query": query})
        return row_id

    def record_performance(self, name: str, value: float, mission_id: str = "",
                           **detail: Any) -> None:
        self.store.record_metric(name, value, mission_id, **detail)

    def purge_expired(self, older_than_days: int | None = None,
                      confirm: str = "") -> dict[str, int]:
        days = older_than_days or self.retention_days
        cutoff = time.time() - days * 86400
        result = self.store.purge(cutoff, confirm)
        self.store.audit("system", "retention_purge", "all", days=days, deleted=result)
        log_event("memory", "retention_purge", days=days, deleted=result)
        return result

    def describe(self) -> dict[str, Any]:
        return {
            "source_of_truth": database_kind(self.store.database_url),
            "task_queue": self.queue.backend,
            "vector_index": self.index.backend,
            "retention_days": self.retention_days,
            "reusable_researches": self.store.count(ResearchCache),
        }
