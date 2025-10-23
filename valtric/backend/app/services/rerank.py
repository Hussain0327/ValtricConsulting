import httpx
from typing import Any, Sequence

from app.settings import settings
import structlog


logger = structlog.get_logger(__name__)


class RerankError(RuntimeError):
    pass


HTTP_TIMEOUT = httpx.Timeout(connect=3.0, read=25.0, write=10.0, pool=3.0)
HTTP_LIMITS = httpx.Limits(max_connections=100, max_keepalive_connections=20)


async def rerank_documents(query: str, documents: Sequence[str], top_k: int = 5) -> list[dict[str, Any]]:
    """Apply Cohere Rerank v3 when available, otherwise fall back to a local BGE reranker."""
    if not documents:
        return []

    if settings.rerank_provider in {None, "", "none"}:
        logger.info("rerank_disabled", provider=settings.rerank_provider or "none")
        return [{"index": idx, "document": doc, "relevance_score": 0.0} for idx, doc in enumerate(documents[:top_k])]

    if settings.rerank_provider == "cohere" and settings.cohere_api_key:
        return await _cohere_rerank(query, documents, top_k)

    logger.info("rerank_fallback_bge", provider=settings.rerank_provider)
    return await _bge_rerank(query, documents, top_k)


async def _cohere_rerank(query: str, documents: Sequence[str], top_k: int) -> list[dict[str, Any]]:
    url = f"{settings.cohere_base_url.rstrip('/')}/rerank"
    headers = {
        "Authorization": f"Bearer {settings.cohere_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.rerank_model,
        "query": query,
        "documents": list(documents),
        "top_n": top_k,
    }

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, limits=HTTP_LIMITS) as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.error("cohere_rerank_failed", error=str(exc))
            raise RerankError("Cohere rerank request failed.") from exc

    data = response.json()
    results = data.get("results", [])
    ranked = []
    for item in results:
        idx = item.get("index")
        if idx is None or idx >= len(documents):
            continue
        ranked.append(
            {
                "index": idx,
                "document": documents[idx],
                "relevance_score": item.get("relevance_score", 0.0),
            }
        )
    return ranked


async def _bge_rerank(query: str, documents: Sequence[str], top_k: int) -> list[dict[str, Any]]:
    """Fallback to a local BGE reranker if configured, else return original ordering."""
    if not settings.bge_rerank_url:
        logger.warning("bge_rerank_url_missing")
        return [{"index": idx, "document": doc, "relevance_score": 0.0} for idx, doc in enumerate(documents[:top_k])]

    url = settings.bge_rerank_url
    payload = {"query": query, "documents": list(documents), "top_k": top_k}

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, limits=HTTP_LIMITS) as client:
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.error("bge_rerank_failed", error=str(exc))
            return [{"index": idx, "document": doc, "relevance_score": 0.0} for idx, doc in enumerate(documents[:top_k])]

    data = response.json()
    results = data.get("results", [])
    ranked = []
    for item in results:
        idx = item.get("index")
        if idx is None or idx >= len(documents):
            continue
        ranked.append(
            {
                "index": idx,
                "document": documents[idx],
                "relevance_score": item.get("score", item.get("relevance_score", 0.0)),
            }
        )
    if not ranked:
        return [{"index": idx, "document": doc, "relevance_score": 0.0} for idx, doc in enumerate(documents[:top_k])]
    return ranked
