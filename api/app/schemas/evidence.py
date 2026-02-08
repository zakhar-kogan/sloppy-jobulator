from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class EvidenceIn(BaseModel):
    discovery_id: str | None = None
    kind: str
    uri: str
    content_hash: str
    captured_at: datetime
    content_type: str | None = None
    byte_size: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceAccepted(BaseModel):
    evidence_id: str
