from __future__ import annotations

import json
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict


class TriagePlan(BaseModel):
    """Structured plan returned by the DeepSeek triage model."""

    model_config = ConfigDict(extra="forbid")

    objective: Optional[str] = None
    required_comps: List[str] = Field(default_factory=list)
    missing_data: List[str] = Field(default_factory=list)
    queries: List[str] = Field(default_factory=list)
    risk_flags: List[str] = Field(default_factory=list)
    route_suggestion: Optional[str] = Field(default=None, pattern="^(easy|hard)$")
    confidence: Optional[float] = None


def parse_triage_plan(raw: str) -> TriagePlan:
    """Parse DeepSeek triage output enforcing a strict schema."""
    raw_str = (raw or "").strip()
    if not raw_str:
        raise ValueError("empty_triage_payload")
    try:
        return TriagePlan.model_validate_json(raw_str)
    except Exception as exc:  # noqa: BLE001
        try:
            data = json.loads(raw_str)
        except Exception as inner_exc:  # noqa: BLE001
            raise ValueError("triage_not_json") from inner_exc
        if isinstance(data, dict) and "triage_plan" in data:
            try:
                return TriagePlan.model_validate(data["triage_plan"])
            except Exception as inner_inner:  # noqa: BLE001
                raise ValueError("triage_plan_invalid") from inner_inner
        raise ValueError("triage_schema_mismatch") from exc
