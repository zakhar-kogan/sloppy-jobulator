from datetime import datetime

from pydantic import BaseModel, Field


class PostingOut(BaseModel):
    id: str
    title: str
    organization_name: str
    canonical_url: str
    status: str = "active"
    tags: list[str] = Field(default_factory=list)
    created_at: datetime
