import pytest
from unittest.mock import AsyncMock, ANY

from app.services.foundry.pipeline import ingest_deal_payload, IngestError


class DummySession:
    def __init__(self):
        self._id = 1

    def add(self, obj):
        # emulate primary key assignment on flush
        if getattr(obj, "id", None) is None:
            setattr(obj, "id", self._id)
            self._id += 1

    async def flush(self):
        return None

    async def commit(self):
        return None

    async def refresh(self, obj):
        return None


@pytest.mark.asyncio
async def test_ingest_requires_deal_payload():
    session = DummySession()
    with pytest.raises(IngestError):
        await ingest_deal_payload(session, {})


@pytest.mark.asyncio
async def test_ingest_requires_documents():
    session = DummySession()
    with pytest.raises(IngestError):
        await ingest_deal_payload(session, {"deal": {"name": "X", "industry": "SaaS", "price": 1.0, "ebitda": 0.1}})


@pytest.mark.asyncio
async def test_ingest_calls_supabase_bulk_upserts(monkeypatch):
    session = DummySession()
    payload = {
        "deal": {"name": "Example", "industry": "SaaS", "price": 1.2, "ebitda": 0.2},
        "documents": [
            {
                "source_name": "doc.txt",
                "mime_type": "text/plain",
                "chunks": [
                    {
                        "ord": 0,
                        "text": "Sample chunk",
                        "embedding": [0.1, 0.2, 0.3],
                        "embedding_model": "text-embedding-3-small",
                    }
                ],
            }
        ],
    }

    mock_client = AsyncMock()
    monkeypatch.setattr("app.services.foundry.pipeline.get_supabase_client", lambda: mock_client)

    result = await ingest_deal_payload(session, payload)

    assert result["documents_ingested"] == 1
    assert result["chunks_ingested"] == 1
    assert result["embeddings_ingested"] == 1

    mock_client.bulk_upsert.assert_any_call("documents", ANY)
    mock_client.bulk_upsert.assert_any_call("chunks", ANY)
    mock_client.bulk_upsert.assert_any_call("embeddings", ANY, on_conflict="chunk_id")
