from typing import Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, Field, field_validator


class DealIn(BaseModel):
    name: str
    industry: str
    price: float = Field(ge=0)
    ebitda: float = Field(ge=0)
    currency: str = "USD"
    description: str | None = None


class DealOut(DealIn):
    id: int


class AnalysisRequest(BaseModel):
    deal_id: int
    question: str = "Is this valuation reasonable?"


Conclusion = Literal["cheap", "fair", "rich", "expensive", "uncertain", "undetermined"]


class CompCitation(BaseModel):
    source_id: str = Field(pattern=r"^chunk:")
    name: Optional[str] = None
    ticker: Optional[str] = None


class AnalysisV1(BaseModel):
    conclusion: Conclusion
    implied_multiple: float
    range: Tuple[float, float]
    reasoning: str
    comps_used: List[CompCitation]
    risk_flags: List[str] = Field(default_factory=list)
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    @field_validator("risk_flags", mode="before")
    @classmethod
    def _clean_risk_flags(cls, value: List[str] | None) -> List[str]:
        if not value:
            return []
        cleaned: List[str] = []
        for item in value:
            if item is None:
                continue
            cleaned.append(str(item).strip())
        return cleaned


class AnalysisOut(AnalysisV1):
    """Backwards-compatible alias used by legacy routes/tests."""


class ChatRequest(BaseModel):
    session_id: str
    deal_id: int
    message: str


class ChatResponse(BaseModel):
    schema_version: Literal["chat_v1.0"] = "chat_v1.0"
    intent: Literal["valuation", "data_request", "small_talk", "non_valuation"]
    path: Literal["easy", "hard"]
    metrics: Dict[str, float]
    analysis: Optional[AnalysisV1] = None
    reply_text: Optional[str] = None
