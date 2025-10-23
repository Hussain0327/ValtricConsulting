import httpx
from typing import Sequence

from app.settings import settings
import structlog


logger = structlog.get_logger(__name__)


class EmbeddingError(RuntimeError):
    pass


async def embed_texts(texts: Sequence[str]) -> list[list[float]]:
    """Call OpenAI embeddings endpoint for a batch of texts."""
    if not texts:
        return []

    if not settings.openai_api_key:
        raise EmbeddingError("OPENAI_API_KEY is not configured.")

    url = f"{settings.openai_base_url.rstrip('/')}/embeddings"
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }
    payload = {"model": settings.embedding_model, "input": list(texts)}

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.error("embedding_request_failed", error=str(exc))
            raise EmbeddingError("Failed to fetch embeddings.") from exc

    data = response.json()
    items = data.get("data", [])
    if len(items) != len(texts):
        logger.warning(
            "embedding_count_mismatch",
            requested=len(texts),
            received=len(items),
        )

    return [item["embedding"] for item in items]
