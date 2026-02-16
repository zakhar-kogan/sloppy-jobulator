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
CandidateAgeBucket = Literal["lt_24h", "d1_3", "d3_7", "gt_7d"]

PostingStatus = Literal["active", "stale", "archived", "closed"]


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


class CandidateMergeRequest(BaseModel):
    secondary_candidate_id: str
    reason: str | None = None


class CandidateOverrideRequest(BaseModel):
    state: CandidateState
    reason: str | None = None
    posting_status: PostingStatus | None = None


class CandidateEventOut(BaseModel):
    id: int
    entity_type: str
    entity_id: str | None = None
    event_type: str
    actor_type: str
    actor_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class CandidateFacetOut(BaseModel):
    value: str
    count: int


class CandidateFacetsOut(BaseModel):
    total: int
    states: list[CandidateFacetOut] = Field(default_factory=list)
    sources: list[CandidateFacetOut] = Field(default_factory=list)
    ages: list[CandidateFacetOut] = Field(default_factory=list)
