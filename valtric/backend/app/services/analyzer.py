from __future__ import annotations

import time
from typing import Any, Dict, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import AnalysisV1, CompCitation
from app.services.consultant import analyze_valuation
from app.services.retrieve import get_similar_chunks
from app.services.validation import sanitize_analysis_payload

_RETRIEVAL_HARD_TERMS = [
    "comp",
    "compare",
    "fx",
    "eur",
    "portfolio",
    "multi-year",
    "multi year",
    "2025",
    "2026",
    "2027",
    "scenario",
    "sensitivity",
]


def _should_require_retrieval(question: str | None) -> bool:
    if not question:
        return False
    text = question.lower()
    return any(term in text for term in _RETRIEVAL_HARD_TERMS)


def _fallback_citations(comps: list[dict[str, Any]], limit: int = 3) -> list[CompCitation]:
    citations: list[CompCitation] = []
    for comp in comps:
        chunk_id = comp.get("chunk_id") or comp.get("id")
        if not chunk_id:
            continue
        citation = CompCitation(source_id=f"chunk:{chunk_id}")
        source_name = comp.get("source") or comp.get("meta", {}).get("section")
        if source_name:
            citation.name = source_name
        citations.append(citation)
        if len(citations) >= limit:
            break
    return citations


async def analyze_core(deal: Any, question: str, db: AsyncSession | None) -> Tuple[AnalysisV1, Dict[str, Any]]:
    """Run retrieval + consultant analysis and return structured output plus metadata."""
    t0 = time.perf_counter()

    retrieval_required = _should_require_retrieval(question)
    deal_payload = _coerce_deal_payload(deal)

    comps = await get_similar_chunks(
        deal_payload,
        question=question,
        db=db,
    )
    retrieval_hits = len(comps)
    retrieval_required = retrieval_required or bool(retrieval_hits)

    raw_output, consultant_meta = await analyze_valuation(
        deal_payload,
        comps,
        question,
    )

    baseline_multiple = deal_payload["price"] / deal_payload["ebitda"] if deal_payload["ebitda"] > 0 else 0.0

    try:
        sanitized = sanitize_analysis_payload(
            raw_output,
            baseline_multiple=baseline_multiple,
            retrieval_required=retrieval_required,
            retrieval_hits=retrieval_hits,
        )
    except ValueError:
        fallback = _fallback_citations(comps)
        if not fallback:
            raise
        raw_output = raw_output or {}
        raw_output["comps_used"] = [c.model_dump() for c in fallback]
        risk_flags = list(raw_output.get("risk_flags") or [])
        if "fallback_citations_injected" not in risk_flags:
            risk_flags.append("fallback_citations_injected")
        raw_output["risk_flags"] = risk_flags
        if raw_output.get("confidence") is None or raw_output.get("confidence", 0.0) > 0.6:
            raw_output["confidence"] = 0.55
        sanitized = sanitize_analysis_payload(
            raw_output,
            baseline_multiple=baseline_multiple,
            retrieval_required=retrieval_required,
            retrieval_hits=retrieval_hits,
        )

    analysis_model = AnalysisV1.model_validate(sanitized)

    overall_ms = (time.perf_counter() - t0) * 1000.0
    meta = {
        "path": consultant_meta.get("path", "easy"),
        "timings": consultant_meta.get("timings", {}),
        "triage_confidence": consultant_meta.get("triage_confidence"),
        "retrieval_hits": retrieval_hits,
        "retrieval_required": retrieval_required,
        "overall_ms": overall_ms,
        "citations": len(analysis_model.comps_used),
    }
    return analysis_model, meta


def _coerce_deal_payload(deal: Any) -> Dict[str, Any]:
    if isinstance(deal, dict):
        data = deal
    else:
        data = {
            "id": getattr(deal, "id", None),
            "price": getattr(deal, "price", None),
            "ebitda": getattr(deal, "ebitda", None),
            "industry": getattr(deal, "industry", None),
            "name": getattr(deal, "name", None),
        }

    def _to_float(value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    return {
        "id": data.get("id"),
        "price": _to_float(data.get("price")),
        "ebitda": _to_float(data.get("ebitda")),
        "industry": data.get("industry") or "",
        "name": data.get("name") or "",
    }
