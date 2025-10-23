from app.schemas import AnalysisV1


def enforce_evidence_rule(analysis: AnalysisV1, retrieval_hits: int) -> AnalysisV1:
    """
    Ensure that when retrieval finds evidence we cite it.
    Raises ValueError if the requirement is not met.
    """
    if retrieval_hits > 0 and len(analysis.comps_used) == 0:
        raise ValueError("evidence_required: retrieval_hits>0 but comps_used is empty")
    return analysis
