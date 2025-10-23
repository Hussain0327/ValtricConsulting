from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.integrations.supabase import get_supabase_client, vector_to_pg
from app.settings import settings


class IngestError(ValueError):
    pass


async def ingest_deal_payload(db: AsyncSession, payload: dict[str, Any]) -> dict[str, Any]:
    """
    Persist a deal + document payload to the local database and Supabase vector store.

    Expected payload shape:
    {
        "deal": {... DealIn schema ...},
        "documents": [
            {
                "source_name": "...",
                "mime_type": "application/pdf",
                "chunks": [
                    {
                        "ord": 0,
                        "text": "...",
                        "meta": {...},
                        "hash": "...",
                        "embedding": [...],
                        "embedding_model": "text-embedding-3-large",
                        "snapshot_id": "optional-uuid"
                    }
                ]
            }
        ]
    }
    """

    deal_payload = payload.get("deal")
    documents_payload = payload.get("documents") or []
    if not deal_payload:
        raise IngestError("deal payload is required")
    if not documents_payload:
        raise IngestError("documents payload is required")

    now = datetime.now(timezone.utc)
    deal = models.Deal(
        org_id=deal_payload.get("org_id", 1),
        name=deal_payload["name"],
        industry=deal_payload["industry"],
        price=deal_payload["price"],
        ebitda=deal_payload["ebitda"],
        currency=deal_payload.get("currency", "USD"),
        description=deal_payload.get("description"),
    )
    db.add(deal)
    await db.flush()

    supabase_docs: list[dict[str, Any]] = []
    supabase_chunks: list[dict[str, Any]] = []
    supabase_embeddings: list[dict[str, Any]] = []

    for document_payload in documents_payload:
        source_name = document_payload.get("source_name")
        mime_type_raw = document_payload.get("mime_type", "application/octet-stream")
        mime_type = mime_type_raw[:50]
        if not source_name:
            raise IngestError("document.source_name is required")

        document = models.Document(
            deal_id=deal.id,
            source_name=source_name,
            mime_type=mime_type,
            created_at=document_payload.get("created_at", now),
        )
        db.add(document)
        await db.flush()

        supabase_docs.append(
            {
                "id": document.id,
                "deal_id": document.deal_id,
                "source_name": document.source_name,
                "mime_type": document.mime_type,
                "created_at": document.created_at.isoformat(),
            }
        )

        for chunk_payload in document_payload.get("chunks", []):
            text = chunk_payload.get("text")
            if not text:
                raise IngestError("chunk.text is required")

            ord_value = int(chunk_payload.get("ord", 0))
            chunk_hash = chunk_payload.get("hash") or _hash_text(text)
            chunk_meta = chunk_payload.get("meta") or {}

            chunk = models.Chunk(
                document_id=document.id,
                ord=ord_value,
                text=text,
                meta=chunk_meta,
                hash=chunk_hash,
            )
            db.add(chunk)
            await db.flush()

            supabase_chunks.append(
                {
                    "id": chunk.id,
                    "document_id": chunk.document_id,
                    "ord": chunk.ord,
                    "text": chunk.text,
                    "meta": chunk.meta,
                    "hash": chunk.hash,
                }
            )

            embedding = chunk_payload.get("embedding")
            if embedding:
                embedding_model = chunk_payload.get("embedding_model", settings.embedding_model)
                snapshot_id = chunk_payload.get("snapshot_id")

                db.add(models.Embedding(chunk_id=chunk.id, vector=embedding))

                supabase_embedding = {
                    "chunk_id": chunk.id,
                    "vector": vector_to_pg(embedding),
                    "model_name": embedding_model,
                    "dim": len(embedding),
                }
                if snapshot_id:
                    supabase_embedding["snapshot_id"] = snapshot_id
                supabase_embeddings.append(supabase_embedding)

    await db.commit()

    supabase_client = get_supabase_client()
    if supabase_client:
        if supabase_docs:
            await supabase_client.bulk_upsert("documents", supabase_docs)
        if supabase_chunks:
            await supabase_client.bulk_upsert("chunks", supabase_chunks)
        if supabase_embeddings:
            await supabase_client.bulk_upsert("embeddings", supabase_embeddings, on_conflict="chunk_id")

    return {
        "deal_id": deal.id,
        "documents_ingested": len(supabase_docs),
        "chunks_ingested": len(supabase_chunks),
        "embeddings_ingested": len(supabase_embeddings),
    }


def _hash_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()
