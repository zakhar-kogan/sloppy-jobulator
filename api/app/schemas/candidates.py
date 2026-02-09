from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

CandidateState = Literal[
    "discovered",
    "processed",
    "publishable",
    "published",
    "rejected",
    "closed",
    "archived",
    "needs_review",
]


class CandidateOut(BaseModel):
    id: str
    state: str
    dedupe_confidence: float | None = None
    risk_flags: list[str] = Field(default_factory=list)
    extracted_fields: dict[str, Any] = Field(default_factory=dict)
    discovery_ids: list[str] = Field(default_factory=list)
    posting_id: str | None = None
    created_at: datetime
    updated_at: datetime


class CandidatePatchRequest(BaseModel):
    state: CandidateState
    reason: str | None = None
