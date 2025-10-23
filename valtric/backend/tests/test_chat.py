import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app import models
from app.services import chat_agent
from app.schemas import AnalysisV1, CompCitation


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def session_maker():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(models.Deal.__table__.create)
        await conn.run_sync(models.Conversation.__table__.create)
        await conn.run_sync(models.Message.__table__.create)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield maker
    finally:
        await engine.dispose()


@pytest.mark.anyio("asyncio")
async def test_simple_chat_creates_conversation(session_maker):
    async with session_maker() as session:
        result = await chat_agent.chat(
            message="Hello there!",
            conversation_id=None,
            deal_id=None,
            session=session,
        )
        assert result["model_used"] == "assistant"
        assert "conversation_id" in result


@pytest.mark.anyio("asyncio")
async def test_valuation_path_uses_analysis(session_maker, monkeypatch):
    async with session_maker() as session:
        deal = models.Deal(
            id=1,
            org_id=1,
            name="Test Deal",
            industry="SaaS",
            price=100.0,
            ebitda=10.0,
            currency="USD",
            description="Demo",
        )
        session.add(deal)
        await session.commit()

        async def fake_analyze_core(_deal, _question, _db):
            analysis = AnalysisV1(
                conclusion="fair",
                implied_multiple=10.0,
                range=(9.0, 11.0),
                reasoning="Sample reasoning",
                comps_used=[CompCitation(source_id="chunk:1")],
                risk_flags=[],
                confidence=0.6,
            )
            meta = {"path": "easy", "retrieval_hits": 1, "overall_ms": 12.0}
            return analysis, meta

        monkeypatch.setattr("app.services.chat_agent.analyze_core", fake_analyze_core)

        result = await chat_agent.chat(
            message="Is Deal 1 priced fairly?",
            conversation_id=None,
            deal_id=1,
            session=session,
        )

        assert result["model_used"] == "valuation-agent"
        assert result["metadata"]["route"] == "valuation"
        assert result["metadata"]["analysis"]["conclusion"] == "fair"


@pytest.mark.anyio("asyncio")
async def test_deal_qa_returns_sources(session_maker, monkeypatch):
    async with session_maker() as session:
        deal = await session.get(models.Deal, 1)
        if deal is None:
            deal = models.Deal(
                id=1,
                org_id=1,
                name="Test Deal",
                industry="SaaS",
                price=100.0,
                ebitda=10.0,
                currency="USD",
                description="Demo",
            )
            session.add(deal)
            await session.commit()

        async def fake_get_chunks(_deal, question, db, top_k=5):
            return [
                {"chunk_id": "123", "text": "Revenue grew 25% year over year.", "source": "Q2 MD&A"},
                {"chunk_id": "456", "text": "EBITDA margin at 18%.", "source": "Management notes"},
            ]

        monkeypatch.setattr("app.services.chat_agent.get_similar_chunks", fake_get_chunks)

        result = await chat_agent.chat(
            message="What do the documents say about revenue?",
            conversation_id=None,
            deal_id=1,
            session=session,
        )

        assert result["model_used"] == "retrieval-agent"
        assert result["metadata"]["hits"] == 2
        assert len(result["metadata"]["top_sources"]) == 2
