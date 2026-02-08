from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DiscoveryEvent(BaseModel):
    origin_module_id: str
    external_id: str | None = None
    discovered_at: datetime
    url: str | None = None
    title_hint: str | None = None
    text_hint: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DiscoveryAccepted(BaseModel):
    discovery_id: str
    normalized_url: str | None
    canonical_hash: str | None
