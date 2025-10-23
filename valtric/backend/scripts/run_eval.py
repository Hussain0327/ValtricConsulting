"""
Structured evaluation harness for the valuation API.

Usage:
    source .venv/bin/activate
    python -m scripts.run_eval [--prompts ../eval/prompts.jsonl] [--port 9000]
"""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import uvicorn

from app.main import app


@dataclass
class EvalCase:
    name: str
    payload: dict[str, Any]
    expectations: dict[str, Any]

    @classmethod
    def from_line(cls, line: str) -> "EvalCase":
        data = json.loads(line)
        return cls(
            name=data["name"],
            payload=data["payload"],
            expectations=data.get("expectations", {}),
        )


async def run_case(client: httpx.AsyncClient, case: EvalCase) -> tuple[bool, str]:
    resp = await client.post("/analyze", json=case.payload, timeout=120.0)
    if resp.status_code != 200:
        return False, f"HTTP {resp.status_code}: {resp.text}"

    data = resp.json()
    try:
        validate_response(data)
        check_expectations(case, data)
        return True, json.dumps(data)
    except AssertionError as exc:
        return False, f"{exc}\nResponse: {json.dumps(data, indent=2)}"


def validate_response(data: dict[str, Any]) -> None:
    allowed = {"conclusion", "implied_multiple", "range", "reasoning", "comps_used", "risk_flags", "confidence"}
    extra = set(data.keys()) - allowed
    assert not extra, f"Unexpected keys: {sorted(extra)}"
    assert isinstance(data.get("conclusion"), str), "conclusion must be string"
    assert isinstance(data.get("implied_multiple"), (int, float)), "implied_multiple must be number"
    rng = data.get("range")
    assert isinstance(rng, list) and len(rng) == 2, "range must be [low, high]"
    assert all(isinstance(x, (int, float)) for x in rng), "range entries must be numeric"
    assert isinstance(data.get("reasoning"), str), "reasoning must be string"
    comps = data.get("comps_used")
    assert isinstance(comps, list), "comps_used must be list"
    for comp in comps:
        assert isinstance(comp, dict), "comps_used entries must be objects"
        assert isinstance(comp.get("source_id"), str) and comp["source_id"].startswith("chunk:"), \
            "each comp must include source_id starting with chunk:"
    risks = data.get("risk_flags")
    assert isinstance(risks, list), "risk_flags must be list"
    confidence = data.get("confidence")
    assert isinstance(confidence, (int, float)) and 0.0 <= confidence <= 1.0, "confidence must be 0<=x<=1"


def check_expectations(case: EvalCase, data: dict[str, Any]) -> None:
    exp = case.expectations
    if "min_citations" in exp:
        assert len(data["comps_used"]) >= exp["min_citations"], \
            f"{case.name}: expected at least {exp['min_citations']} citations"
    if exp.get("require_no_citable_flag"):
        assert "no_citable_evidence" in data["risk_flags"], \
            f"{case.name}: missing no_citable_evidence flag"
    if "max_confidence" in exp:
        assert data["confidence"] <= exp["max_confidence"], \
            f"{case.name}: confidence {data['confidence']} exceeds {exp['max_confidence']}"
    if "min_confidence" in exp:
        assert data["confidence"] >= exp["min_confidence"], \
            f"{case.name}: confidence {data['confidence']} below {exp['min_confidence']}"


async def serve_and_run(cases: list[EvalCase], port: int) -> list[tuple[EvalCase, bool, str]]:
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    server_task = asyncio.create_task(server.serve())
    await asyncio.sleep(0.5)  # give the server time to start

    results: list[tuple[EvalCase, bool, str]] = []
    async with httpx.AsyncClient(base_url=f"http://127.0.0.1:{port}") as client:
        for case in cases:
            success, detail = await run_case(client, case)
            results.append((case, success, detail))

    server.should_exit = True
    await server_task
    return results


def load_cases(path: Path) -> list[EvalCase]:
    cases: list[EvalCase] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            stripped = line.strip()
            if not stripped:
                continue
            cases.append(EvalCase.from_line(stripped))
    return cases


def main() -> None:
    parser = argparse.ArgumentParser(description="Run structured evaluation cases against the valuation API.")
    parser.add_argument("--prompts", type=Path, default=Path(__file__).resolve().parents[2] / "eval" / "prompts.jsonl")
    parser.add_argument("--port", type=int, default=9000)
    args = parser.parse_args()

    cases = load_cases(args.prompts)
    if not cases:
        print("No evaluation cases found.")
        return

    results = asyncio.run(serve_and_run(cases, port=args.port))

    total = len(results)
    passed = sum(1 for _, success, _ in results if success)
    print(f"\nEvaluation complete: {passed}/{total} passed.")
    for case, success, detail in results:
        status = "PASS" if success else "FAIL"
        print(f" - {status}: {case.name}")
        if not success:
            print(f"   {detail}")


if __name__ == "__main__":
    main()
