import pytest

from app.services import retrieve


@pytest.mark.asyncio
async def test_get_similar_chunks_returns_empty_when_embedding_fails(monkeypatch):
    async def fake_embed_texts(texts):
        return []

    monkeypatch.setattr(retrieve, "embed_texts", fake_embed_texts)

    result = await retrieve.get_similar_chunks(
        {"price": 1.2, "ebitda": 0.2, "industry": "SaaS", "name": "Deal"},
        question="simple question",
        db=None,
    )
    assert result == []


@pytest.mark.asyncio
async def test_get_similar_chunks_uses_supabase(monkeypatch):
    async def fake_embed_texts(texts):
        return [[0.1, 0.2, 0.3]]

    async def fake_supabase_vector_search(vector, top_k, deal_id=None):
        return [
            {"chunk_id": 1, "text": "Doc 1", "meta": {}, "document_id": 10, "source": "source A", "score": 0.9},
            {"chunk_id": 2, "text": "Doc 2", "meta": {}, "document_id": 11, "source": "source B", "score": 0.8},
        ]

    async def fake_rerank_documents(query, documents, top_k):
        return [{"index": 1, "document": documents[1], "relevance_score": 0.95}]

    monkeypatch.setattr(retrieve, "embed_texts", fake_embed_texts)
    monkeypatch.setattr(retrieve, "_supabase_vector_search", fake_supabase_vector_search)
    monkeypatch.setattr(retrieve, "rerank_documents", fake_rerank_documents)

    # Ensure settings allow supabase branch
    monkeypatch.setattr(retrieve.settings, "supabase_url", "https://example.supabase.co")
    monkeypatch.setattr(retrieve.settings, "supabase_service_role_key", "service-key")

    result = await retrieve.get_similar_chunks(
        {"id": 99, "price": 1.2, "ebitda": 0.2, "industry": "SaaS", "name": "Deal"},
        question="compare with fx",
        db=None,
    )
    assert len(result) == 2
    assert {r["chunk_id"] for r in result} == {1, 2}
