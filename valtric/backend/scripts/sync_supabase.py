import asyncio
from typing import Any

from sqlalchemy import select

from app import models
from app.db import SessionLocal
from app.integrations.supabase import get_supabase_client, vector_to_pg
from app.settings import settings


async def gather_records() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    async with SessionLocal() as session:
        documents = (await session.execute(select(models.Document))).scalars().all()
        chunks = (await session.execute(select(models.Chunk))).scalars().all()
        embeddings = (await session.execute(select(models.Embedding))).scalars().all()

    document_rows = [
        {
            "id": doc.id,
            "deal_id": doc.deal_id,
            "source_name": doc.source_name,
            "mime_type": doc.mime_type,
            "created_at": getattr(doc, "created_at", None).isoformat() if getattr(doc, "created_at", None) else None,
        }
        for doc in documents
    ]

    chunk_rows = [
        {
            "id": chunk.id,
            "document_id": chunk.document_id,
            "ord": chunk.ord,
            "text": chunk.text,
            "meta": chunk.meta,
            "hash": chunk.hash,
        }
        for chunk in chunks
    ]

    embedding_rows = []
    for embedding in embeddings:
        vector = getattr(embedding, "vector", None)
        if vector is None:
            continue
        values = list(vector)
        embedding_rows.append(
            {
                "chunk_id": embedding.chunk_id,
                "vector": vector_to_pg(values),
                "model_name": settings.embedding_model,
                "dim": len(values),
            }
        )

    return document_rows, chunk_rows, embedding_rows


async def main() -> None:
    client = get_supabase_client()
    if not client:
        raise SystemExit("Supabase configuration is missing (SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY).")

    documents, chunks, embeddings = await gather_records()

    print(f"Upserting {len(documents)} documents, {len(chunks)} chunks, {len(embeddings)} embeddings to Supabase...")

    if documents:
        await client.bulk_upsert("documents", documents)
    if chunks:
        await client.bulk_upsert("chunks", chunks)
    if embeddings:
        await client.bulk_upsert("embeddings", embeddings, on_conflict="chunk_id")

    print("Supabase sync complete.")


if __name__ == "__main__":
    asyncio.run(main())
