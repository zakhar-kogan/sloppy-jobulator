from typing import Any

from pydantic import BaseModel, Field


class JobOut(BaseModel):
    id: str
    kind: str
    target_type: str
    target_id: str | None = None
    inputs_json: dict[str, Any] = Field(default_factory=dict)
    status: str


class ClaimRequest(BaseModel):
    lease_seconds: int = 120


class ResultRequest(BaseModel):
    result_json: dict[str, Any] | None = None
    error_json: dict[str, Any] | None = None
    status: str
