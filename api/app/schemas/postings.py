from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

PostingStatus = Literal["active", "stale", "archived", "closed"]
PostingSortBy = Literal["created_at", "updated_at", "deadline", "published_at"]
SortDir = Literal["asc", "desc"]


class PostingListOut(BaseModel):
    id: str
    title: str
    organization_name: str
    canonical_url: str
    status: PostingStatus = "active"
    country: str | None = None
    remote: bool = False
    tags: list[str] = Field(default_factory=list)
    updated_at: datetime
    created_at: datetime


class PostingDetailOut(BaseModel):
    id: str
    candidate_id: str | None = None
    title: str
    canonical_url: str
    normalized_url: str
    canonical_hash: str
    organization_name: str
    sector: str | None = None
    degree_level: str | None = None
    opportunity_kind: str | None = None
    country: str | None = None
    region: str | None = None
    city: str | None = None
    remote: bool = False
    tags: list[str] = Field(default_factory=list)
    areas: list[str] = Field(default_factory=list)
    description_text: str | None = None
    application_url: str | None = None
    deadline: datetime | None = None
    source_refs: list[dict[str, Any]] = Field(default_factory=list)
    status: PostingStatus = "active"
    published_at: datetime | None = None
    updated_at: datetime
    created_at: datetime


class PostingPatchRequest(BaseModel):
    status: PostingStatus
    reason: str | None = None
