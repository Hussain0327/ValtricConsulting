import math

import pytest

from app.services.consultant import _should_escalate
from app.services.validation import sanitize_analysis_payload


def test_sanitize_applies_baseline_guardrail_when_no_citations():
    payload = {
        "conclusion": "cheap",
        "implied_multiple": 7.3,
        "range": [6.0, 8.0],
        "reasoning": "Sample reasoning",
        "comps_used": ["bad-format", {"source_id": "not-a-chunk"}],
        "risk_flags": [],
        "confidence": 0.9,
    }

    result = sanitize_analysis_payload(
        payload,
        baseline_multiple=6.0,
        retrieval_required=False,
        retrieval_hits=0,
    )

    assert result["implied_multiple"] == pytest.approx(6.0)
    assert result["range"] == [pytest.approx(5.5), pytest.approx(6.5)]
    assert "no_citable_evidence" in result["risk_flags"]
    assert result["confidence"] <= 0.5
    assert result["comps_used"] == []


def test_sanitize_preserves_valid_citations_and_confidence():
    payload = {
        "conclusion": "fair",
        "implied_multiple": 6.4,
        "range": [5.8, 6.9],
        "reasoning": "Backed by comps",
        "comps_used": [
            {"source_id": "chunk:abc", "name": "Comp A"},
            {"source_id": "chunk:def", "ticker": "CMPB"},
        ],
        "risk_flags": ["fx-risk"],
        "confidence": 0.7,
    }

    result = sanitize_analysis_payload(
        payload,
        baseline_multiple=6.0,
        retrieval_required=True,
        retrieval_hits=2,
    )

    assert len(result["comps_used"]) == 2
    assert all(item["source_id"].startswith("chunk:") for item in result["comps_used"])
    assert result["confidence"] == pytest.approx(0.7)
    assert "no_citable_evidence" not in result["risk_flags"]
    assert math.isclose(result["implied_multiple"], 6.4, rel_tol=1e-6)
    assert result["range"] == [pytest.approx(5.8), pytest.approx(6.9)]


def test_sanitize_raises_when_hits_without_citations():
    payload = {
        "conclusion": "cheap",
        "implied_multiple": 7.0,
        "range": [6.0, 8.0],
        "reasoning": "retrieval yielded evidence but citations missing",
        "comps_used": [{"name": "Bad Comp"}],  # missing source_id
        "risk_flags": [],
        "confidence": 0.9,
    }

    with pytest.raises(ValueError):
        sanitize_analysis_payload(
            payload,
            baseline_multiple=6.0,
            retrieval_required=True,
            retrieval_hits=2,
        )


@pytest.mark.parametrize(
    ("complexity", "payload", "comps", "expected"),
    [
        ("easy", {"confidence": 0.9}, [], False),
        ("hard", None, [], True),
        ("hard", {"confidence": 0.6, "comps_used": ["comp"]}, [], False),
        ("hard", {"confidence": 0.4, "comps_used": ["comp"]}, [], True),
        ("hard", {"confidence": 0.8, "comps_used": []}, [], True),
    ],
)
def test_should_escalate(complexity, payload, comps, expected):
    assert _should_escalate(complexity, payload, comps) is expected
