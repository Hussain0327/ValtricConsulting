import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.db import SessionLocal, get_db
from app.schemas import AnalysisRequest, AnalysisV1
from app.services.analyzer import analyze_core
from app.services.enforce import enforce_evidence_rule
from app.settings import settings
import structlog

router = APIRouter(prefix="/analyze", tags=["analyze"])
logger = structlog.get_logger(__name__)


@router.post("", response_model=AnalysisV1)
async def analyze(body: AnalysisRequest, db: AsyncSession = Depends(get_db)):
    boundary_start = time.perf_counter()
    res = await db.execute(select(models.Deal).where(models.Deal.id == body.deal_id))
    deal = res.scalar_one_or_none()
    if not deal:
        raise HTTPException(404, "deal not found")

    try:
        analysis, meta = await analyze_core(deal, body.question, db)
        enforce_evidence_rule(analysis, meta.get("retrieval_hits", 0))
    except ValueError as exc:
        logger.error(
            "analysis_evidence_violation",
            deal_id=deal.id,
            retrieval_hits=meta.get("retrieval_hits") if "meta" in locals() else None,
            detail=str(exc),
        )
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    analysis_dict = analysis.model_dump()
    async with SessionLocal() as session:
        session.add(models.Analysis(deal_id=deal.id, kind="valuation", prompt="valuation-agent", output=analysis_dict))
        await session.commit()

    logger.info(
        "analysis_sanitized",
        deal_id=deal.id,
        retrieval_required=meta.get("retrieval_required"),
        retrieval_hits=meta.get("retrieval_hits"),
        cited_comps=len(analysis.comps_used),
        baseline_freeze=len(analysis.comps_used) == 0,
        confidence=analysis.confidence,
        path=meta.get("path"),
        consultant_ms=meta.get("overall_ms"),
        schema_version=settings.response_schema_version,
    )
    boundary_ms = (time.perf_counter() - boundary_start) * 1000.0
    logger.info(
        "analyze_boundary_timing",
        deal_id=deal.id,
        question_len=len(body.question or ""),
        overall_ms=boundary_ms,
    )
    return analysis
