from __future__ import annotations

from typing import Any

ALLOWED_RESULT_KEYS = {
    "conclusion",
    "implied_multiple",
    "range",
    "reasoning",
    "comps_used",
    "risk_flags",
    "confidence",
}


def sanitize_analysis_payload(
    payload: dict[str, Any],
    *,
    baseline_multiple: float,
    retrieval_required: bool,
    retrieval_hits: int,
) -> dict[str, Any]:
    """Coerce the LLM payload into the strict schema expected by clients/tests."""
    result: dict[str, Any] = {}

    conclusion = payload.get("conclusion")
    result["conclusion"] = str(conclusion) if conclusion is not None else "undetermined"

    implied = _as_float(payload.get("implied_multiple"), default=baseline_multiple)

    raw_range = payload.get("range")
    if isinstance(raw_range, (list, tuple)) and len(raw_range) == 2:
        lo = _as_float(raw_range[0], default=implied - 0.5)
        hi = _as_float(raw_range[1], default=implied + 0.5)
    else:
        lo = implied - 0.5
        hi = implied + 0.5

    reasoning = payload.get("reasoning")
    result["reasoning"] = reasoning if isinstance(reasoning, str) else ""

    raw_comps = payload.get("comps_used") or []
    comps_used: list[dict[str, Any]] = []
    if isinstance(raw_comps, list):
        for item in raw_comps:
            if not isinstance(item, dict):
                continue
            source_id = item.get("source_id")
            if not isinstance(source_id, str) or not source_id.startswith("chunk:"):
                continue
            cleaned: dict[str, Any] = {"source_id": source_id}
            if item.get("name"):
                cleaned["name"] = str(item["name"])
            if item.get("ticker"):
                cleaned["ticker"] = str(item["ticker"])
            comps_used.append(cleaned)

    # When retrieval produced hits but no valid citations, raise so upstream can alert.
    if retrieval_required and retrieval_hits > 0 and not comps_used:
        raise ValueError("retrieval_hits_without_citations")

    raw_risks = payload.get("risk_flags") or []
    risks: list[str] = []
    if isinstance(raw_risks, list):
        for entry in raw_risks:
            if entry is None:
                continue
            risks.append(str(entry))
    elif raw_risks:
        risks.append(str(raw_risks))

    confidence = _as_float(payload.get("confidence"), default=0.45)
    confidence = max(0.0, min(1.0, confidence))

    if not comps_used:
        implied = baseline_multiple
        lo = baseline_multiple - 0.5
        hi = baseline_multiple + 0.5
        lo = max(0.0, lo)
        confidence = min(confidence, 0.5)
        if "no_citable_evidence" not in risks:
            risks.append("no_citable_evidence")

    # Normalise range ordering and rounding.
    if lo > hi:
        lo, hi = hi, lo
    result["range"] = [_round(lo), _round(hi)]
    result["implied_multiple"] = _round(implied)
    result["comps_used"] = comps_used
    result["risk_flags"] = list(dict.fromkeys(risks))
    result["confidence"] = confidence

    return result


def _as_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _round(value: float, places: int = 6) -> float:
    try:
        return round(float(value), places)
    except (TypeError, ValueError):
        return value
