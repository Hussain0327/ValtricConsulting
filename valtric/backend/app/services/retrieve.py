from __future__ import annotations

from typing import Any, Sequence

import asyncio
import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.services.embed import embed_texts
from app.services.rerank import rerank_documents
from app.settings import settings


logger = structlog.get_logger(__name__)

HTTP_TIMEOUT = httpx.Timeout(connect=3.0, read=25.0, write=10.0, pool=3.0)
HTTP_LIMITS = httpx.Limits(max_connections=100, max_keepalive_connections=20)
_RERANK_SEM = asyncio.Semaphore(settings.rerank_max_concurrency)


async def get_similar_chunks(
    deal: dict[str, Any],
    *,
    question: str | None = None,
    db: AsyncSession | None = None,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Retrieve semantically similar chunks for the deal via Supabase (preferred) or local pgvector fallback."""
    query_text = _compose_query_text(deal, question)

    try:
        embeddings = await embed_texts([query_text])
    except Exception as exc:  # noqa: BLE001
        logger.warning("embedding_failed", error=str(exc))
        return []

    if not embeddings:
        logger.info("embedding_empty_output", query=query_text)
        return []

    query_vector = embeddings[0]

    hits: list[dict[str, Any]] = []

    deal_id = deal.get("id")

    if settings.supabase_url and settings.supabase_service_role_key:
        try:
            supabase_hits = await _supabase_vector_search(
                query_vector,
                top_k=top_k,
                deal_id=deal_id,
            )
            logger.info("supabase_vector_search", hits=len(supabase_hits))
            hits = supabase_hits
        except Exception as exc:  # noqa: BLE001
            logger.warning("supabase_vector_search_failed", error=str(exc))

    if not hits and db is not None:
        try:
            local_hits = await _local_vector_search(
                db,
                query_vector,
                deal_id=deal_id,
                top_k=top_k,
            )
            logger.info("local_vector_search", hits=len(local_hits))
            hits = local_hits
        except Exception as exc:  # noqa: BLE001
            logger.warning("local_vector_search_failed", error=str(exc))

    if not hits:
        return []

    use_rerank = settings.rerank_provider not in {None, "", "none"}
    ranked_hits, rerank_info = await _maybe_rerank(query_text, hits, use_rerank=use_rerank)
    logger.info(
        "rerank_summary",
        provider=rerank_info.get("provider"),
        used_rerank=rerank_info.get("used_rerank"),
        fallback_used=rerank_info.get("fallback_used"),
        candidate_k=rerank_info.get("candidate_k"),
        rerank_k=rerank_info.get("rerank_k"),
    )
    return ranked_hits


def _compose_query_text(deal: dict[str, Any], question: str | None) -> str:
    parts: list[str] = []
    if question:
        parts.append(question)
    name = deal.get("name")
    industry = deal.get("industry")
    price = deal.get("price")
    ebitda = deal.get("ebitda")

    details = []
    if name:
        details.append(f"name: {name}")
    if industry:
        details.append(f"industry: {industry}")
    if price is not None:
        details.append(f"price: {price}")
    if ebitda is not None:
        details.append(f"ebitda: {ebitda}")
    if details:
        parts.append(" | ".join(details))
    return " :: ".join(parts) if parts else "valuation analysis"


async def _supabase_vector_search(query_vector: Sequence[float], *, top_k: int, deal_id: Any | None) -> list[dict[str, Any]]:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return []

    headers = {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {
        "query_embedding": query_vector,
        "match_count": top_k,
    }
    if deal_id is not None:
        payload["target_deal_id"] = deal_id

    fn = settings.supabase_match_function or "match_chunks"
    url = f"{settings.supabase_url.rstrip('/')}/rest/v1/rpc/{fn}"
    
    logger.info("supabase_rpc_call", fn=fn, payload=payload, deal_id=deal_id)

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, limits=HTTP_LIMITS) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()

    data = response.json()
    if isinstance(data, dict):
        data = data.get("results", [])

    results: list[dict[str, Any]] = []
    for item in data or []:
        results.append(
            {
                "chunk_id": item.get("chunk_id") or item.get("id"),
                "text": item.get("text") or item.get("content"),
                "meta": item.get("meta") or {},
                "document_id": item.get("document_id"),
                "source": item.get("source_name") or item.get("source"),
                "score": item.get("similarity") or item.get("score"),
            }
        )
    return results


async def _local_vector_search(
    db: AsyncSession,
    query_vector: Sequence[float],
    *,
    deal_id: Any | None,
    top_k: int,
) -> list[dict[str, Any]]:
    distance = models.Embedding.vector.cosine_distance(query_vector)
    stmt = (
        select(
            models.Chunk.id.label("chunk_id"),
            models.Chunk.text,
            models.Chunk.meta,
            models.Chunk.document_id,
            models.Document.source_name.label("source"),
            distance.label("distance"),
        )
        .join(models.Embedding, models.Embedding.chunk_id == models.Chunk.id)
        .join(models.Document, models.Document.id == models.Chunk.document_id)
        .order_by(distance.asc())  # smaller distance => more similar
        .limit(top_k)
    )
    if deal_id is not None:
        stmt = stmt.where(models.Document.deal_id == deal_id)

    rows = (await db.execute(stmt)).mappings().all()
    results: list[dict[str, Any]] = []
    for row in rows:
        distance_val = row.get("distance")
        score = 1.0 - float(distance_val) if distance_val is not None else None
        results.append(
            {
                "chunk_id": row["chunk_id"],
                "text": row["text"],
                "meta": row.get("meta") or {},
                "document_id": row.get("document_id"),
                "source": row.get("source"),
                "score": score,
            }
        )
    return results


async def _maybe_rerank(query_text: str, hits: list[dict[str, Any]], *, use_rerank: bool) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    documents = [hit.get("text", "") for hit in hits]
    info = {
        "provider": settings.rerank_provider or "none",
        "used_rerank": False,
        "fallback_used": False,
        "candidate_k": len(documents[:5]),
        "rerank_k": 0,
    }

    if not use_rerank or not documents:
        return hits, info

    try:
        async with _RERANK_SEM:
            reranked = await rerank_documents(query_text, documents, top_k=len(documents))
    except Exception as exc:  # noqa: BLE001
        logger.warning("rerank_failed", error=str(exc))
        info["fallback_used"] = True
        return hits, info

    ordered: list[dict[str, Any]] = []
    for item in reranked:
        idx = item.get("index")
        if idx is None or idx >= len(hits):
            continue
        payload = hits[idx].copy()
        payload["rerank_score"] = item.get("relevance_score")
        ordered.append(payload)

    if ordered and len(ordered) == len(hits):
        top_vec = [h.get("chunk_id") for h in hits[:5]]
        top_rer = [h.get("chunk_id") for h in ordered[:5]]
        info["used_rerank"] = top_vec != top_rer
        info["rerank_k"] = len(ordered[:5])
        return ordered, info

    if ordered:
        info["fallback_used"] = True

    return hits, info
