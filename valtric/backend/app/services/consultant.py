import json
import time
from typing import Any, Iterable, Optional

import asyncio
import httpx
import structlog

from app.settings import settings
from app.prompts import SYSTEM_PROMPT
from app.services.triage import parse_triage_plan, TriagePlan


logger = structlog.get_logger(__name__)

HTTP_TIMEOUT = httpx.Timeout(connect=3.0, read=45.0, write=10.0, pool=3.0)
HTTP_LIMITS = httpx.Limits(max_connections=100, max_keepalive_connections=20)
_LLM_SEM = asyncio.Semaphore(settings.llm_max_concurrency)


async def analyze_valuation(
    deal: dict[str, Any],
    comps: list[dict[str, Any]],
    question: str | None = None,
) -> dict[str, Any]:
    """Adaptive valuation analysis using GPT-5 Nano for easy cases and DeepSeek escalation for hard cases."""
    timings: dict[str, float] = {}
    overall_start = time.perf_counter()

    baseline = _heuristic_baseline(deal, comps)
    complexity = _classify_request(question, deal, comps)
    final_payload: dict[str, Any] = baseline
    logger.info(
        "analysis_classification",
        complexity=complexity,
        routing_version=settings.routing_version,
        classifier="legacy_heuristic",
    )

    triage_summary = "DeepSeek triage not executed; using baseline heuristics."
    deepseek_payload: dict[str, Any] | None = None
    triage_plan: Optional[TriagePlan] = None

    if complexity == "hard" and settings.deepseek_api_key:
        ds_start = time.perf_counter()
        try:
            ds_prompt = _render_deepseek_prompt(deal, comps, baseline, question)
            async with _LLM_SEM:
                deepseek_response = await _call_deepseek_json(
                    ds_prompt,
                    effort=settings.primary_reasoning_hard,
                )
            try:
                triage_plan = parse_triage_plan(deepseek_response)
                triage_summary = _summarize_plan(triage_plan)
                deepseek_payload = None
                logger.info(
                    "triage_plan_parsed",
                    confidence=triage_plan.confidence,
                    suggested_route=triage_plan.route_suggestion,
                    missing=len(triage_plan.missing_data),
                    queries=len(triage_plan.queries),
                )
            except ValueError as plan_exc:
                logger.info("triage_plan_parse_failed", error=str(plan_exc))
                deepseek_payload = _coerce_response(deepseek_response, baseline, comps)
                triage_summary = _summarize_payload(deepseek_payload)
        except Exception as exc:  # noqa: BLE001 broad to ensure fallback
            logger.warning("deepseek_triage_failed", error=str(exc))
            deepseek_payload = None
        finally:
            timings["deepseek_ms"] = (time.perf_counter() - ds_start) * 1000
    elif complexity == "hard":
        triage_summary = "DeepSeek triage unavailable; falling back to baseline heuristic."
    else:
        timings["deepseek_ms"] = 0.0

    triage_ran = triage_plan is not None or deepseek_payload is not None
    skip_reason = None
    if complexity != "hard":
        skip_reason = "not_hard"
    elif not settings.deepseek_api_key:
        skip_reason = "missing_api_key"
    elif not triage_ran:
        skip_reason = "triage_unavailable"

    logger.info(
        "triage_result",
        ran=triage_ran,
        skip_reason=skip_reason,
        triage_confidence=triage_plan.confidence if triage_plan and triage_plan.confidence is not None else None,
    )

    final_payload = deepseek_payload or baseline
    escalate_to_gpt = _should_escalate(complexity, final_payload, comps)

    should_call_gpt = settings.openai_api_key and (
        complexity == "easy" or escalate_to_gpt
    )

    if should_call_gpt:
        gpt_start = time.perf_counter()
        try:
            final_prompt = _render_final_prompt(deal, comps, baseline, triage_summary, complexity)
            effort = (
                settings.secondary_reasoning_easy if complexity == "easy" else settings.secondary_reasoning_hard
            )
            verbosity = (
                settings.secondary_verbosity_easy if complexity == "easy" else settings.secondary_verbosity_hard
            )
            async with _LLM_SEM:
                llm_response = await _call_gpt5(final_prompt, effort=effort, verbosity=verbosity)
            seed_payload = deepseek_payload or baseline
            final_payload = _coerce_response(llm_response, seed_payload, comps)
        except Exception as exc:  # noqa: BLE001
            logger.warning("gpt5_final_failed", error=str(exc))
        finally:
            timings["gpt5_ms"] = (time.perf_counter() - gpt_start) * 1000
    else:
        timings["gpt5_ms"] = 0.0

    timings["overall_ms"] = (time.perf_counter() - overall_start) * 1000
    logger.info("analyze_pipeline_timings", complexity=complexity, **timings)
    triage_confidence = triage_plan.confidence if triage_plan and triage_plan.confidence is not None else None
    logger.info(
        "final_stage_decision",
        used_gpt5=bool(should_call_gpt),
        prompt_version=settings.prompt_version,
        routing_version=settings.routing_version,
        triage_confidence=triage_confidence,
    )

    meta = {
        "path": complexity,
        "timings": timings,
        "triage_confidence": triage_confidence,
    }

    return final_payload, meta


def _heuristic_baseline(deal: dict[str, Any], comps: Iterable[dict[str, Any]]) -> dict[str, Any]:
    e = float(deal.get("ebitda") or 0.0)
    p = float(deal.get("price") or 0.0)
    multiple = p / (e if e > 1e-9 else 1e-9)
    verdict = "fair" if 8 <= multiple <= 12 else ("rich" if multiple > 12 else "cheap")
    comp_names = [c.get("name") for c in comps if c.get("name")]
    return {
        "conclusion": verdict,
        "implied_multiple": round(multiple, 2),
        "range": (max(round(multiple - 1.0, 2), 0.0), round(multiple + 1.0, 2)),
        "reasoning": "Baseline multiple heuristic derived from price/EBITDA.",
        "comps_used": comp_names,
        "risk_flags": [],
        "confidence": 0.5,
    }


def _classify_request(question: str | None, deal: dict[str, Any], comps: Iterable[dict[str, Any]]) -> str:
    text = (question or "").lower()
    hard_terms = [
        "compare",
        "versus",
        "vs",
        "portfolio",
        "multi",
        "scenario",
        "sensitivity",
        "synergy",
        "dilution",
        "dcf",
        "discounted cash",
        "merger",
        "leveraged",
        "fx",
        "currency",
        "hedge",
        "tax",
        "rag",
        "retrieval",
    ]
    if any(term in text for term in hard_terms):
        return "hard"

    # Missing fundamental deal data => treat as higher risk/complex
    if not deal.get("price") or not deal.get("ebitda") or not deal.get("industry"):
        return "hard"

    # Long-form or multi-question prompts are likely complex
    if text.count("?") > 1 or len(text.split()) > 40:
        return "hard"

    return "easy"


def _render_deepseek_prompt(
    deal: dict[str, Any],
    comps: list[dict[str, Any]],
    baseline: dict[str, Any],
    question: str | None,
) -> str:
    return (
        "You are a valuation associate. Return strict JSON (no markdown) following this schema:\n"
        "{"
        '"conclusion": "<cheap|fair|rich>", '
        '"implied_multiple": <float>, '
        '"range": [<float>, <float>], '
        '"reasoning": "<<=80 words>", '
        '"comps_used": ["<name>", ...], '
        '"risk_flags": ["<risk>", ...], '
        '"confidence": <float between 0 and 1>'
        "}\n"
        "Ground your answer in the supplied deal data, comparable snippets, and baseline heuristic. "
        "If data gaps exist, note them in risk_flags and reduce confidence. "
        "Do not invent sources beyond the provided data.\n\n"
        f"Question: {question or 'Is this valuation reasonable?'}\n"
        f"Deal: {json.dumps(deal, default=str)}\n"
        f"Comparable set: {json.dumps(comps, default=str)}\n"
        f"Baseline heuristic: {json.dumps(baseline, default=str)}"
    )


def _summarize_payload(payload: dict[str, Any]) -> str:
    conclusion = payload.get("conclusion")
    confidence = payload.get("confidence")
    comps_used = payload.get("comps_used") or []
    comps_preview = ", ".join(comps_used[:3]) if comps_used else "no comps cited"
    return (
        f"DeepSeek first-pass: conclusion={conclusion}, confidence={confidence}, comps={comps_preview}."
    )


def _summarize_plan(plan: TriagePlan) -> str:
    missing = ", ".join(plan.missing_data[:3]) if plan.missing_data else "none"
    comps = ", ".join(plan.required_comps[:3]) if plan.required_comps else "none"
    return (
        "Triage Plan -> "
        f"route={plan.route_suggestion or 'unknown'}, "
        f"confidence={plan.confidence}, "
        f"missing={missing}, comps={comps}"
    )


def _render_final_prompt(
    deal: dict[str, Any],
    comps: list[dict[str, Any]],
    baseline: dict[str, Any],
    triage_summary: str,
    complexity: str,
) -> str:
    return (
        "You are a senior investment banking analyst. Produce a concise valuation memo structured as strict JSON that "
        "matches the following schema: {\n"
        '  "conclusion": "<cheap|fair|rich>",\n'
        '  "implied_multiple": <float>,\n'
        '  "range": [<float>, <float>],\n'
        '  "reasoning": "<short narrative>",\n'
        '  "comps_used": ["<name>", ...],\n'
        '  "risk_flags": ["<risk>", ...],\n'
        '  "confidence": <float between 0 and 1>\n'
        "}\n\n"
        "Requirements:\n"
        "- Use the deal & comparable data exactly as given.\n"
        "- Factor in the triage summary if provided, but verify it independently.\n"
        "- If data is missing, note it in risk_flags and lower confidence.\n"
        "- Keep reasoning under 120 words.\n\n"
        f"Deal: {json.dumps(deal, default=str)}\n"
        f"Comparable set: {json.dumps(comps, default=str)}\n"
        f"Baseline heuristic: {json.dumps(baseline, default=str)}\n"
        f"Triage summary: {triage_summary}\n"
        f"Complexity classification: {complexity}\n\n"
        "Return only JSON. Do not include markdown."
    )


async def _call_deepseek_json(prompt: str, effort: str | None = None) -> str:
    url = f"{settings.deepseek_base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.deepseek_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.primary_model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You produce concise valuation memos as strict minified JSON. "
                    "Never return markdown or commentary outside the JSON object."
                ),
            },
            {"role": "user", "content": prompt},
        ],
    }
    if effort:
        payload["reasoning"] = {"effort": effort}

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, limits=HTTP_LIMITS) as client:
        response = await client.post(url, headers=headers, json=payload)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "deepseek_triage_http_error",
                status=exc.response.status_code,
                body=exc.response.text,
            )
            raise

    data = response.json()
    choices = data.get("choices", [])
    if not choices:
        raise RuntimeError("DeepSeek response missing choices.")
    return choices[0]["message"]["content"]


def _should_escalate(complexity: str, payload: dict[str, Any], comps: list[dict[str, Any]]) -> bool:
    if complexity != "hard":
        return False
    if payload is None:
        return True
    confidence = payload.get("confidence")
    if confidence is None or confidence < 0.55:
        return True
    if not payload.get("comps_used") and not comps:
        return True
    return False


async def _call_gpt5(prompt: str, *, effort: str | None = None, verbosity: str = "medium") -> str:
    url = f"{settings.openai_base_url.rstrip('/')}/responses"
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.secondary_model or settings.model_name,
        "text": {"verbosity": verbosity},
        "input": [
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": SYSTEM_PROMPT,
                    }
                ],
            },
            {"role": "user", "content": [{"type": "input_text", "text": prompt}]},
        ],
    }
    if effort:
        payload["reasoning"] = {"effort": effort}

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, limits=HTTP_LIMITS) as client:
        response = await client.post(url, headers=headers, json=payload)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "gpt5_http_error",
                status=exc.response.status_code,
                body=exc.response.text,
            )
            raise

    data = response.json()
    if "output_text" in data:
        return "".join(data["output_text"])

    output = data.get("output", [])
    chunks: list[str] = []
    for item in output:
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"}:
                chunks.append(content.get("text", ""))
    if chunks:
        return "".join(chunks)

    raise RuntimeError("GPT-5 response did not include output text.")


def _coerce_response(raw: str, baseline: dict[str, Any], comps: list[dict[str, Any]]) -> dict[str, Any]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning("gpt5_invalid_json", response=raw, error=str(exc))
        return baseline

    try:
        implied = float(parsed.get("implied_multiple", baseline["implied_multiple"]))
    except (TypeError, ValueError):
        implied = baseline["implied_multiple"]

    range_raw = parsed.get("range", baseline["range"])
    try:
        lo, hi = range_raw
        lo_f = float(lo)
        hi_f = float(hi)
        computed_range = (lo_f, hi_f)
    except (TypeError, ValueError, IndexError):
        computed_range = baseline["range"]

    try:
        confidence = float(parsed.get("confidence", baseline["confidence"]))
    except (TypeError, ValueError):
        confidence = baseline["confidence"]

    result = {
        "conclusion": parsed.get("conclusion", baseline["conclusion"]),
        "implied_multiple": implied,
        "range": computed_range,
        "reasoning": parsed.get("reasoning", baseline["reasoning"]),
        "comps_used": parsed.get(
            "comps_used",
            [c.get("name") for c in comps if c.get("name")],
        ),
        "risk_flags": parsed.get("risk_flags", baseline["risk_flags"]),
        "confidence": confidence,
    }
    return result
