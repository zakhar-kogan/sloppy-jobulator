from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

ModuleTrustLevel = Literal["trusted", "semi_trusted", "untrusted"]
ModuleKind = Literal["connector", "processor"]
JobKind = Literal["dedupe", "extract", "enrich", "check_freshness", "resolve_url_redirects"]
JobStatus = Literal["queued", "claimed", "done", "failed", "dead_letter"]


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


class URLNormalizationOverrideOut(BaseModel):
    domain: str
    strip_query_params: list[str] = Field(default_factory=list)
    strip_query_prefixes: list[str] = Field(default_factory=list)
    strip_www: bool
    force_https: bool
    enabled: bool
    created_at: datetime
    updated_at: datetime


class URLNormalizationOverrideUpsertRequest(BaseModel):
    strip_query_params: list[str] = Field(default_factory=list)
    strip_query_prefixes: list[str] = Field(default_factory=list)
    strip_www: bool = False
    force_https: bool = False
    enabled: bool = True


class URLNormalizationOverrideEnabledPatchRequest(BaseModel):
    enabled: bool


class ModuleOut(BaseModel):
    id: str
    module_id: str
    name: str
    kind: ModuleKind
    enabled: bool
    scopes: list[str] = Field(default_factory=list)
    trust_level: ModuleTrustLevel
    created_at: datetime
    updated_at: datetime


class ModuleEnabledPatchRequest(BaseModel):
    enabled: bool


class AdminJobOut(BaseModel):
    id: str
    kind: JobKind
    target_type: str
    target_id: str | None = None
    status: JobStatus
    attempt: int
    locked_by_module_id: str | None = None
    lease_expires_at: datetime | None = None
    next_run_at: datetime
    created_at: datetime
    updated_at: datetime


class AdminJobsMaintenanceOut(BaseModel):
    count: int
