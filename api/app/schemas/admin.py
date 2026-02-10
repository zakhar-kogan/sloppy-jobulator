from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

ModuleTrustLevel = Literal["trusted", "semi_trusted", "untrusted"]


class SourceTrustPolicyOut(BaseModel):
    source_key: str
    trust_level: ModuleTrustLevel
    auto_publish: bool
    requires_moderation: bool
    rules_json: dict[str, Any] = Field(default_factory=dict)
    enabled: bool
    created_at: datetime
    updated_at: datetime


class SourceTrustPolicyUpsertRequest(BaseModel):
    trust_level: ModuleTrustLevel
    auto_publish: bool
    requires_moderation: bool
    rules_json: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class SourceTrustPolicyEnabledPatchRequest(BaseModel):
    enabled: bool
