from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any

import asyncpg  # type: ignore[import-untyped]
from asyncpg import exceptions as pg_exc

from app.core.config import get_settings
from app.core.urls import canonical_hash
from app.services.dedupe import (
    DedupeCandidateSnapshot,
    DedupePolicyDecision,
    evaluate_merge_policy,
    extract_contact_domains,
    extract_named_entities,
)


class RepositoryError(Exception):
    """Base repository error."""


class RepositoryUnavailableError(RepositoryError):
    """Raised when the database is unavailable or not configured."""


class RepositoryNotFoundError(RepositoryError):
    """Raised when the requested entity does not exist."""


class RepositoryConflictError(RepositoryError):
    """Raised when an operation violates state transition rules."""


class RepositoryForbiddenError(RepositoryError):
    """Raised when an operation is not permitted for the actor."""


class RepositoryValidationError(RepositoryError):
    """Raised when payload validation fails before persistence."""


@dataclass(slots=True)
class MachineCredentialRecord:
    module_db_id: str
    module_id: str
    scopes: list[str]
    key_hash: str


@dataclass(slots=True)
class SourceTrustPolicyRecord:
    source_key: str
    trust_level: str
    auto_publish: bool
    requires_moderation: bool
    rules_json: dict[str, Any]
    matched_fallback: bool


SOURCE_POLICY_TRUST_LEVELS = {"trusted", "semi_trusted", "untrusted"}
SOURCE_POLICY_RULE_KEYS = {
    "min_confidence",
}
MODULE_KINDS = {"connector", "processor"}
JOB_KINDS = {"dedupe", "extract", "enrich", "check_freshness", "resolve_url_redirects"}
JOB_STATUSES = {"queued", "claimed", "done", "failed", "dead_letter"}
ADMIN_JOB_FILTER_STATUSES = {"queued", "claimed", "done", "failed"}
ADMIN_JOB_FILTER_KINDS = {"extract", "check_freshness", "resolve_url_redirects"}
QUEUE_AGE_BUCKETS = ("lt_24h", "d1_3", "d3_7", "gt_7d")
URL_OVERRIDE_TOKEN_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
URL_OVERRIDE_DOMAIN_RE = re.compile(r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


class PostgresRepository:
    def __init__(
        self,
        database_url: str | None,
        min_pool_size: int,
        max_pool_size: int,
        job_max_attempts: int,
        job_retry_base_seconds: int,
        job_retry_max_seconds: int,
        freshness_check_interval_hours: int,
        freshness_stale_after_hours: int,
        freshness_archive_after_hours: int,
    ) -> None:
        self.database_url = database_url
        self.min_pool_size = min_pool_size
        self.max_pool_size = max_pool_size
        self.job_max_attempts = max(1, job_max_attempts)
        self.job_retry_base_seconds = max(0, job_retry_base_seconds)
        self.job_retry_max_seconds = max(0, job_retry_max_seconds)
        self.freshness_check_interval_hours = max(1, freshness_check_interval_hours)
        self.freshness_stale_after_hours = max(1, freshness_stale_after_hours)
        self.freshness_archive_after_hours = max(self.freshness_stale_after_hours, freshness_archive_after_hours)
        self._pool: asyncpg.Pool | None = None

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def get_machine_credentials(self, module_id: str) -> list[MachineCredentialRecord]:
        pool = await self._get_pool()
        rows = await pool.fetch(
            """
            select
              m.id::text as module_db_id,
              m.module_id,
              m.scopes,
              mc.key_hash
            from modules m
            join module_credentials mc on mc.module_id = m.id
            where m.module_id = $1
              and m.enabled = true
              and mc.is_active = true
              and mc.revoked_at is null
              and (mc.expires_at is null or mc.expires_at > now())
            """,
            module_id,
        )
        return [
            MachineCredentialRecord(
                module_db_id=row["module_db_id"],
                module_id=row["module_id"],
                scopes=list(row["scopes"] or []),
                key_hash=row["key_hash"],
            )
            for row in rows
        ]

    async def upsert_source_trust_policy(
        self,
        *,
        source_key: str,
        trust_level: str,
        auto_publish: bool,
        requires_moderation: bool,
        rules_json: dict[str, Any],
        enabled: bool = True,
        actor_user_id: str | None = None,
    ) -> SourceTrustPolicyRecord:
        normalized_source_key = self._coerce_text(source_key)
        if not normalized_source_key:
            raise RepositoryValidationError("source_key must be a non-empty string")

        normalized_trust_level = self._coerce_text(trust_level)
        if normalized_trust_level not in SOURCE_POLICY_TRUST_LEVELS:
            raise RepositoryValidationError(
                "trust_level must be one of: trusted, semi_trusted, untrusted",
            )

        normalized_rules_json = self._validate_source_trust_policy_rules_json(rules_json, strict=True)
        normalized_actor_user_id = self._coerce_text(actor_user_id)
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                existing_row = await conn.fetchrow(
                    """
                    select
                      id::text as id,
                      source_key,
                      trust_level::text as trust_level,
                      auto_publish,
                      requires_moderation,
                      rules_json,
                      enabled
                    from source_trust_policy
                    where source_key = $1
                    for update
                    """,
                    normalized_source_key,
                )
                if existing_row:
                    row = await conn.fetchrow(
                        """
                        update source_trust_policy
                        set
                          trust_level = $2::module_trust_level,
                          auto_publish = $3,
                          requires_moderation = $4,
                          rules_json = $5::jsonb,
                          enabled = $6
                        where source_key = $1
                        returning
                          id::text as id,
                          source_key,
                          trust_level::text as trust_level,
                          auto_publish,
                          requires_moderation,
                          rules_json,
                          enabled
                        """,
                        normalized_source_key,
                        normalized_trust_level,
                        bool(auto_publish),
                        bool(requires_moderation),
                        json.dumps(normalized_rules_json),
                        bool(enabled),
                    )
                    operation = "updated"
                else:
                    row = await conn.fetchrow(
                        """
                        insert into source_trust_policy (
                          source_key,
                          trust_level,
                          auto_publish,
                          requires_moderation,
                          rules_json,
                          enabled
                        )
                        values ($1, $2::module_trust_level, $3, $4, $5::jsonb, $6)
                        returning
                          id::text as id,
                          source_key,
                          trust_level::text as trust_level,
                          auto_publish,
                          requires_moderation,
                          rules_json,
                          enabled
                        """,
                        normalized_source_key,
                        normalized_trust_level,
                        bool(auto_publish),
                        bool(requires_moderation),
                        json.dumps(normalized_rules_json),
                        bool(enabled),
                    )
                    operation = "created"

                if not row:
                    raise RepositoryConflictError("failed to upsert source trust policy")

                normalized_row_rules = self._validate_source_trust_policy_rules_json(row["rules_json"], strict=False)
                if normalized_actor_user_id:
                    previous_payload: dict[str, Any] | None = None
                    if existing_row:
                        previous_payload = {
                            "trust_level": existing_row["trust_level"],
                            "auto_publish": bool(existing_row["auto_publish"]),
                            "requires_moderation": bool(existing_row["requires_moderation"]),
                            "enabled": bool(existing_row["enabled"]),
                            "rules_json": self._validate_source_trust_policy_rules_json(
                                existing_row["rules_json"],
                                strict=False,
                            ),
                        }
                    await self._record_source_trust_policy_event(
                        conn=conn,
                        policy_id=row["id"],
                        event_type="policy_upserted",
                        actor_user_id=normalized_actor_user_id,
                        payload={
                            "source_key": row["source_key"],
                            "operation": operation,
                            "trust_level": row["trust_level"],
                            "auto_publish": bool(row["auto_publish"]),
                            "requires_moderation": bool(row["requires_moderation"]),
                            "enabled": bool(row["enabled"]),
                            "rules_json": normalized_row_rules,
                            "previous": previous_payload,
                        },
                    )

                return SourceTrustPolicyRecord(
                    source_key=row["source_key"],
                    trust_level=row["trust_level"],
                    auto_publish=bool(row["auto_publish"]),
                    requires_moderation=bool(row["requires_moderation"]),
                    rules_json=normalized_row_rules,
                    matched_fallback=False,
                )

    async def create_discovery_and_enqueue_extract(
        self,
        *,
        origin_module_db_id: str,
        external_id: str | None,
        discovered_at: datetime,
        url: str | None,
        normalized_url: str | None,
        canonical_hash: str | None,
        title_hint: str | None,
        text_hint: str | None,
        metadata: dict[str, Any],
        actor_module_db_id: str,
        enqueue_redirect_resolution: bool = False,
    ) -> str:
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            async with conn.transaction():
                inserted = False

                if external_id:
                    row = await conn.fetchrow(
                        """
                        insert into discoveries (
                          origin_module_id,
                          external_id,
                          discovered_at,
                          url,
                          normalized_url,
                          canonical_hash,
                          title_hint,
                          text_hint,
                          metadata
                        )
                        values ($1::uuid, $2, $3, $4, $5, $6, $7, $8, $9::jsonb)
                        on conflict (origin_module_id, external_id) where external_id is not null do nothing
                        returning id::text as id
                        """,
                        origin_module_db_id,
                        external_id,
                        discovered_at,
                        url,
                        normalized_url,
                        canonical_hash,
                        title_hint,
                        text_hint,
                        json.dumps(metadata),
                    )
                    if row:
                        discovery_id = row["id"]
                        inserted = True
                    else:
                        existing = await conn.fetchrow(
                            """
                            select id::text as id
                            from discoveries
                            where origin_module_id = $1::uuid and external_id = $2
                            """,
                            origin_module_db_id,
                            external_id,
                        )
                        if not existing:
                            raise RepositoryConflictError("failed to resolve existing discovery after conflict")
                        discovery_id = existing["id"]
                elif normalized_url:
                    row = await conn.fetchrow(
                        """
                        insert into discoveries (
                          origin_module_id,
                          external_id,
                          discovered_at,
                          url,
                          normalized_url,
                          canonical_hash,
                          title_hint,
                          text_hint,
                          metadata
                        )
                        values ($1::uuid, null, $2, $3, $4, $5, $6, $7, $8::jsonb)
                        on conflict (origin_module_id, normalized_url) where external_id is null and normalized_url is not null do nothing
                        returning id::text as id
                        """,
                        origin_module_db_id,
                        discovered_at,
                        url,
                        normalized_url,
                        canonical_hash,
                        title_hint,
                        text_hint,
                        json.dumps(metadata),
                    )
                    if row:
                        discovery_id = row["id"]
                        inserted = True
                    else:
                        existing = await conn.fetchrow(
                            """
                            select id::text as id
                            from discoveries
                            where origin_module_id = $1::uuid
                              and external_id is null
                              and normalized_url = $2
                            """,
                            origin_module_db_id,
                            normalized_url,
                        )
                        if not existing:
                            raise RepositoryConflictError("failed to resolve existing discovery after conflict")
                        discovery_id = existing["id"]
                else:
                    row = await conn.fetchrow(
                        """
                        insert into discoveries (
                          origin_module_id,
                          external_id,
                          discovered_at,
                          url,
                          normalized_url,
                          canonical_hash,
                          title_hint,
                          text_hint,
                          metadata
                        )
                        values ($1::uuid, null, $2, $3, null, null, $4, $5, $6::jsonb)
                        returning id::text as id
                        """,
                        origin_module_db_id,
                        discovered_at,
                        url,
                        title_hint,
                        text_hint,
                        json.dumps(metadata),
                    )
                    discovery_id = row["id"]
                    inserted = True

                if inserted:
                    await conn.execute(
                        """
                        insert into jobs (kind, target_type, target_id, inputs_json)
                        values ('extract', 'discovery', $1::uuid, $2::jsonb)
                        """,
                        discovery_id,
                        json.dumps({"discovery_id": discovery_id}),
                    )
                    if enqueue_redirect_resolution and url:
                        normalization_overrides_json = await self._fetch_enabled_url_normalization_overrides_json(conn=conn)
                        redirect_inputs: dict[str, Any] = {
                            "discovery_id": discovery_id,
                            "url": url,
                            "normalized_url": normalized_url,
                            "canonical_hash": canonical_hash,
                        }
                        if normalization_overrides_json:
                            redirect_inputs["normalization_overrides_json"] = normalization_overrides_json
                        await conn.execute(
                            """
                            insert into jobs (kind, target_type, target_id, inputs_json)
                            values ('resolve_url_redirects', 'discovery', $1::uuid, $2::jsonb)
                            """,
                            discovery_id,
                            json.dumps(redirect_inputs),
                        )
                    await conn.execute(
                        """
                        insert into provenance_events (
                          entity_type,
                          entity_id,
                          event_type,
                          actor_type,
                          actor_id,
                          payload
                        )
                        values ('discovery', $1::uuid, 'ingested', 'machine', $2::uuid, $3::jsonb)
                        """,
                        discovery_id,
                        actor_module_db_id,
                        json.dumps({"external_id": external_id, "normalized_url": normalized_url}),
                    )

                return discovery_id

    async def create_evidence(
        self,
        *,
        discovery_id: str | None,
        kind: str,
        uri: str,
        content_hash: str,
        captured_at: datetime,
        content_type: str | None,
        byte_size: int | None,
        metadata: dict[str, Any],
        actor_module_db_id: str,
    ) -> str:
        pool = await self._get_pool()

        try:
            async with pool.acquire() as conn:
                async with conn.transaction():
                    row = await conn.fetchrow(
                        """
                        insert into evidence (
                          discovery_id,
                          kind,
                          uri,
                          content_hash,
                          captured_at,
                          content_type,
                          byte_size,
                          metadata
                        )
                        values ($1::uuid, $2::evidence_kind, $3, $4, $5, $6, $7, $8::jsonb)
                        returning id::text as id
                        """,
                        discovery_id,
                        kind,
                        uri,
                        content_hash,
                        captured_at,
                        content_type,
                        byte_size,
                        json.dumps(metadata),
                    )
                    evidence_id = row["id"]
                    await conn.execute(
                        """
                        insert into provenance_events (
                          entity_type,
                          entity_id,
                          event_type,
                          actor_type,
                          actor_id,
                          payload
                        )
                        values ('evidence', $1::uuid, 'ingested', 'machine', $2::uuid, $3::jsonb)
                        """,
                        evidence_id,
                        actor_module_db_id,
                        json.dumps({"kind": kind, "uri": uri}),
                    )
                    return evidence_id
        except (pg_exc.ForeignKeyViolationError, pg_exc.InvalidTextRepresentationError, asyncpg.DataError) as exc:
            raise RepositoryConflictError(str(exc)) from exc

    async def list_queued_jobs(self, limit: int) -> list[dict[str, Any]]:
        pool = await self._get_pool()
        rows = await pool.fetch(
            """
            select
              id::text as id,
              kind::text as kind,
              target_type,
              target_id::text as target_id,
              inputs_json,
              status::text as status
            from jobs
            where status = 'queued' and next_run_at <= now()
            order by next_run_at asc, created_at asc
            limit $1
            """,
            limit,
        )
        return [self._job_row_to_dict(row) for row in rows]

    async def claim_job(self, job_id: str, module_db_id: str, lease_seconds: int) -> dict[str, Any]:
        pool = await self._get_pool()

        try:
            async with pool.acquire() as conn:
                async with conn.transaction():
                    row = await conn.fetchrow(
                        """
                        update jobs
                        set
                          status = 'claimed',
                          locked_by_module_id = $2::uuid,
                          locked_at = now(),
                          lease_expires_at = now() + ($3::int * interval '1 second'),
                          attempt = attempt + 1
                        where id = $1::uuid and status = 'queued' and next_run_at <= now()
                        returning
                          id::text as id,
                          kind::text as kind,
                          target_type,
                          target_id::text as target_id,
                          inputs_json,
                          status::text as status
                        """,
                        job_id,
                        module_db_id,
                        lease_seconds,
                    )

                    if not row:
                        exists = await conn.fetchval("select 1 from jobs where id = $1::uuid", job_id)
                        if not exists:
                            raise RepositoryNotFoundError("job not found")
                        raise RepositoryConflictError("job is not claimable")

                    await conn.execute(
                        """
                        insert into provenance_events (
                          entity_type,
                          entity_id,
                          event_type,
                          actor_type,
                          actor_id,
                          payload
                        )
                        values ('job', $1::uuid, 'claimed', 'machine', $2::uuid, $3::jsonb)
                        """,
                        row["id"],
                        module_db_id,
                        json.dumps({"lease_seconds": lease_seconds}),
                    )
                    job = self._job_row_to_dict(row)
                    if job["kind"] == "resolve_url_redirects" and job["target_type"] == "discovery":
                        overrides_json = await self._fetch_enabled_url_normalization_overrides_json(conn=conn)
                        inputs = self._coerce_json_dict(job.get("inputs_json"))
                        if overrides_json:
                            inputs["normalization_overrides_json"] = overrides_json
                        else:
                            inputs.pop("normalization_overrides_json", None)
                        await conn.execute(
                            """
                            update jobs
                            set inputs_json = $2::jsonb
                            where id = $1::uuid
                            """,
                            row["id"],
                            json.dumps(inputs),
                        )
                        job["inputs_json"] = inputs
                    return job
        except (pg_exc.InvalidTextRepresentationError, asyncpg.DataError) as exc:
            raise RepositoryNotFoundError("job not found") from exc

    async def requeue_expired_claimed_jobs(self, module_db_id: str, limit: int) -> int:
        return await self._requeue_expired_claimed_jobs(
            actor_id=module_db_id,
            actor_type="machine",
            limit=limit,
        )

    async def enqueue_due_freshness_jobs(self, module_db_id: str, limit: int) -> int:
        return await self._enqueue_due_freshness_jobs(
            actor_id=module_db_id,
            actor_type="machine",
            limit=limit,
        )

    async def admin_requeue_expired_claimed_jobs(self, *, actor_user_id: str, limit: int) -> int:
        normalized_actor_user_id = self._coerce_text(actor_user_id)
        if not normalized_actor_user_id:
            raise RepositoryValidationError("actor_user_id must be a non-empty string")
        return await self._requeue_expired_claimed_jobs(
            actor_id=normalized_actor_user_id,
            actor_type="human",
            limit=limit,
        )

    async def admin_enqueue_due_freshness_jobs(self, *, actor_user_id: str, limit: int) -> int:
        normalized_actor_user_id = self._coerce_text(actor_user_id)
        if not normalized_actor_user_id:
            raise RepositoryValidationError("actor_user_id must be a non-empty string")
        return await self._enqueue_due_freshness_jobs(
            actor_id=normalized_actor_user_id,
            actor_type="human",
            limit=limit,
        )

    async def _requeue_expired_claimed_jobs(self, *, actor_id: str, actor_type: str, limit: int) -> int:
        pool = await self._get_pool()
        bounded_limit = max(1, min(limit, 1000))

        async with pool.acquire() as conn:
            async with conn.transaction():
                rows = await conn.fetch(
                    """
                    with expired as (
                      select id
                      from jobs
                      where status = 'claimed'
                        and lease_expires_at is not null
                        and lease_expires_at <= now()
                      order by lease_expires_at asc
                      limit $1
                      for update skip locked
                    )
                    update jobs j
                    set
                      status = 'queued',
                      locked_by_module_id = null,
                      locked_at = null,
                      lease_expires_at = null,
                      next_run_at = now()
                    from expired e
                    where j.id = e.id
                    returning j.id::text as id
                    """,
                    bounded_limit,
                )

                for row in rows:
                    await conn.execute(
                        """
                        insert into provenance_events (
                          entity_type,
                          entity_id,
                          event_type,
                          actor_type,
                          actor_id,
                          payload
                        )
                        values ('job', $1::uuid, 'lease_requeued', $2, $3::uuid, $4::jsonb)
                        """,
                        row["id"],
                        actor_type,
                        actor_id,
                        json.dumps({"reason": "lease_expired"}),
                    )
                return len(rows)

    async def _enqueue_due_freshness_jobs(self, *, actor_id: str, actor_type: str, limit: int) -> int:
        pool = await self._get_pool()
        bounded_limit = max(1, min(limit, 1000))

        async with pool.acquire() as conn:
            async with conn.transaction():
                rows = await conn.fetch(
                    """
                    with due_postings as (
                      select p.id, p.status::text as status, p.updated_at, p.created_at
                      from postings p
                      where p.status in ('active', 'stale')
                        and not exists (
                          select 1
                          from jobs pending
                          where pending.kind = 'check_freshness'
                            and pending.target_type = 'posting'
                            and pending.target_id = p.id
                            and pending.status in ('queued', 'claimed')
                        )
                        and not exists (
                          select 1
                          from jobs recent
                          where recent.kind = 'check_freshness'
                            and recent.target_type = 'posting'
                            and recent.target_id = p.id
                            and recent.status in ('done', 'failed', 'dead_letter')
                            and recent.updated_at > now() - ($2::int * interval '1 hour')
                        )
                      order by p.updated_at asc, p.created_at asc
                      limit $1
                      for update skip locked
                    )
                    insert into jobs (kind, target_type, target_id, inputs_json, next_run_at)
                    select
                      'check_freshness',
                      'posting',
                      due.id,
                      jsonb_build_object(
                        'posting_id', due.id::text,
                        'posting_status', due.status,
                        'posting_updated_at', due.updated_at,
                        'stale_after_hours', $3::int,
                        'archive_after_hours', $4::int
                      ),
                      now()
                    from due_postings due
                    returning
                      id::text as id,
                      target_id::text as target_id
                    """,
                    bounded_limit,
                    self.freshness_check_interval_hours,
                    self.freshness_stale_after_hours,
                    self.freshness_archive_after_hours,
                )

                for row in rows:
                    await conn.execute(
                        """
                        insert into provenance_events (
                          entity_type,
                          entity_id,
                          event_type,
                          actor_type,
                          actor_id,
                          payload
                        )
                        values ('job', $1::uuid, 'freshness_enqueued', $2, $3::uuid, $4::jsonb)
                        """,
                        row["id"],
                        actor_type,
                        actor_id,
                        json.dumps(
                            {
                                "posting_id": row["target_id"],
                                "freshness_check_interval_hours": self.freshness_check_interval_hours,
                                "stale_after_hours": self.freshness_stale_after_hours,
                                "archive_after_hours": self.freshness_archive_after_hours,
                            }
                        ),
                    )
                return len(rows)

    async def submit_job_result(
        self,
        job_id: str,
        module_db_id: str,
        status: str,
        result_json: dict[str, Any] | None,
        error_json: dict[str, Any] | None,
    ) -> dict[str, Any]:
        pool = await self._get_pool()

        try:
            async with pool.acquire() as conn:
                async with conn.transaction():
                    claimed = await conn.fetchrow(
                        """
                        select
                          id::text as id,
                          kind::text as kind,
                          target_type,
                          target_id::text as target_id,
                          inputs_json,
                          status::text as status,
                          locked_by_module_id::text as locked_by,
                          attempt
                        from jobs
                        where id = $1::uuid
                        for update
                        """,
                        job_id,
                    )

                    if not claimed:
                        raise RepositoryNotFoundError("job not found")
                    if claimed["status"] != "claimed":
                        raise RepositoryConflictError("job is not in claimed state")
                    if claimed["locked_by"] != module_db_id:
                        raise RepositoryForbiddenError("job claimed by another module")

                    attempt = int(claimed["attempt"])
                    next_run_at: datetime | None = None
                    requested_status = status
                    resolved_status = status
                    retry_delay_seconds: int | None = None
                    redirect_resolution_outcome: dict[str, Any] | None = None

                    if requested_status == "failed":
                        if attempt >= self.job_max_attempts:
                            resolved_status = "failed"
                        else:
                            retry_delay_seconds = self._compute_retry_delay_seconds(attempt=attempt)
                            next_run_at = datetime.now(timezone.utc) + timedelta(seconds=retry_delay_seconds)
                            resolved_status = "queued"

                    row = await conn.fetchrow(
                        """
                        update jobs
                        set
                          status = $2::job_status,
                          result_json = $3::jsonb,
                          error_json = $4::jsonb,
                          locked_by_module_id = null,
                          locked_at = null,
                          lease_expires_at = null,
                          next_run_at = coalesce($5::timestamptz, next_run_at)
                        where id = $1::uuid
                        returning
                          id::text as id,
                          kind::text as kind,
                          target_type,
                          target_id::text as target_id,
                          inputs_json,
                          status::text as status
                        """,
                        job_id,
                        resolved_status,
                        json.dumps(result_json) if result_json is not None else None,
                        json.dumps(error_json) if error_json is not None else None,
                        next_run_at,
                    )

                    if (
                        row["status"] == "done"
                        and row["kind"] == "extract"
                        and row["target_type"] == "discovery"
                        and row["target_id"]
                    ):
                        await self._materialize_extract_projection(
                            conn=conn,
                            job_id=row["id"],
                            discovery_id=row["target_id"],
                            actor_module_db_id=module_db_id,
                            result_json=result_json,
                        )
                    if row["kind"] == "check_freshness" and row["target_type"] == "posting" and row["target_id"]:
                        if row["status"] == "done":
                            await self._apply_freshness_job_result(
                                conn=conn,
                                job_id=row["id"],
                                posting_id=row["target_id"],
                                actor_module_db_id=module_db_id,
                                result_json=result_json,
                            )
                        elif row["status"] == "failed":
                            await self._apply_freshness_dead_letter_fallback(
                                conn=conn,
                                job_id=row["id"],
                                posting_id=row["target_id"],
                                actor_module_db_id=module_db_id,
                                attempt=attempt,
                            )
                    if row["status"] == "done" and row["kind"] == "resolve_url_redirects" and row["target_type"] == "discovery" and row["target_id"]:
                        redirect_resolution_outcome = await self._apply_redirect_resolution_result(
                            conn=conn,
                            job_id=row["id"],
                            discovery_id=row["target_id"],
                            actor_module_db_id=module_db_id,
                            result_json=result_json,
                        )
                        merged_result_json = self._coerce_json_dict(result_json)
                        merged_result_json["repository_outcome"] = redirect_resolution_outcome
                        await conn.execute(
                            """
                            update jobs
                            set result_json = $2::jsonb
                            where id = $1::uuid
                            """,
                            row["id"],
                            json.dumps(merged_result_json),
                        )
                        result_json = merged_result_json

                    await conn.execute(
                        """
                        insert into provenance_events (
                          entity_type,
                          entity_id,
                          event_type,
                          actor_type,
                          actor_id,
                          payload
                        )
                        values ('job', $1::uuid, 'result_submitted', 'machine', $2::uuid, $3::jsonb)
                        """,
                        row["id"],
                        module_db_id,
                        json.dumps(
                            {
                                "requested_status": requested_status,
                                "resolved_status": resolved_status,
                                "attempt": attempt,
                                "max_attempts": self.job_max_attempts,
                                "retry_delay_seconds": retry_delay_seconds,
                                "redirect_resolution_outcome": redirect_resolution_outcome,
                            }
                        ),
                    )
                    if requested_status == "failed" and resolved_status == "queued" and retry_delay_seconds is not None:
                        await conn.execute(
                            """
                            insert into provenance_events (
                              entity_type,
                              entity_id,
                              event_type,
                              actor_type,
                              actor_id,
                              payload
                            )
                            values ('job', $1::uuid, 'retry_scheduled', 'machine', $2::uuid, $3::jsonb)
                            """,
                            row["id"],
                            module_db_id,
                            json.dumps(
                                {
                                    "attempt": attempt,
                                    "max_attempts": self.job_max_attempts,
                                    "retry_delay_seconds": retry_delay_seconds,
                                }
                            ),
                        )
                    return self._job_row_to_dict(row)
        except (pg_exc.InvalidTextRepresentationError, asyncpg.DataError) as exc:
            raise RepositoryNotFoundError("job not found") from exc

    async def _apply_redirect_resolution_result(
        self,
        *,
        conn: asyncpg.Connection,
        job_id: str,
        discovery_id: str,
        actor_module_db_id: str,
        result_json: dict[str, Any] | None,
    ) -> dict[str, Any]:
        payload = result_json if isinstance(result_json, dict) else {}
        resolved_url = self._coerce_text(payload.get("resolved_url"))
        resolved_normalized_url = self._coerce_text(payload.get("resolved_normalized_url"))
        resolved_canonical_hash = self._coerce_text(payload.get("resolved_canonical_hash"))
        outcome: dict[str, Any] = {
            "status": "skipped_missing_resolution",
            "resolver_reason": self._coerce_text(payload.get("reason")),
            "redirect_hop_count": self._coerce_int(payload.get("redirect_hop_count")),
        }
        if not any([resolved_url, resolved_normalized_url, resolved_canonical_hash]):
            return outcome

        discovery = await conn.fetchrow(
            """
            select
              id::text as id,
              origin_module_id::text as origin_module_id,
              external_id,
              url,
              normalized_url,
              canonical_hash
            from discoveries
            where id = $1::uuid
            """,
            discovery_id,
        )
        if not discovery:
            outcome["status"] = "skipped_discovery_not_found"
            return outcome

        next_url = resolved_url or self._coerce_text(discovery["url"])
        next_normalized_url = resolved_normalized_url or self._coerce_text(discovery["normalized_url"])
        next_canonical_hash = resolved_canonical_hash
        if next_canonical_hash is None and next_normalized_url:
            next_canonical_hash = canonical_hash(next_normalized_url)
        if next_canonical_hash is None:
            next_canonical_hash = self._coerce_text(discovery["canonical_hash"])

        current_url = self._coerce_text(discovery["url"])
        current_normalized_url = self._coerce_text(discovery["normalized_url"])
        current_canonical_hash = self._coerce_text(discovery["canonical_hash"])
        if (
            next_url == current_url
            and next_normalized_url == current_normalized_url
            and next_canonical_hash == current_canonical_hash
        ):
            outcome["status"] = "unchanged"
            return outcome

        if discovery["external_id"] is None and next_normalized_url:
            existing = await conn.fetchval(
                """
                select 1
                from discoveries
                where id <> $1::uuid
                  and origin_module_id = $2::uuid
                  and external_id is null
                  and normalized_url = $3
                """,
                discovery_id,
                discovery["origin_module_id"],
                next_normalized_url,
            )
            if existing:
                await conn.execute(
                    """
                    insert into provenance_events (
                      entity_type,
                      entity_id,
                      event_type,
                      actor_type,
                      actor_id,
                      payload
                    )
                    values ('discovery', $1::uuid, 'redirect_resolution_conflict', 'machine', $2::uuid, $3::jsonb)
                    """,
                    discovery_id,
                    actor_module_db_id,
                    json.dumps(
                        {
                            "job_id": job_id,
                            "resolved_url": next_url,
                            "resolved_normalized_url": next_normalized_url,
                            "resolver_reason": self._coerce_text(payload.get("reason")),
                            "redirect_hop_count": self._coerce_int(payload.get("redirect_hop_count")),
                        }
                    ),
                )
                outcome["status"] = "conflict_skipped"
                outcome["resolved_url"] = next_url
                outcome["resolved_normalized_url"] = next_normalized_url
                return outcome

        await conn.execute(
            """
            update discoveries
            set
              url = $2,
              normalized_url = $3,
              canonical_hash = $4,
              updated_at = now()
            where id = $1::uuid
            """,
            discovery_id,
            next_url,
            next_normalized_url,
            next_canonical_hash,
        )
        await conn.execute(
            """
            insert into provenance_events (
              entity_type,
              entity_id,
              event_type,
              actor_type,
              actor_id,
              payload
            )
            values ('discovery', $1::uuid, 'redirect_resolved', 'machine', $2::uuid, $3::jsonb)
            """,
            discovery_id,
            actor_module_db_id,
            json.dumps(
                {
                    "job_id": job_id,
                    "previous_url": current_url,
                    "previous_normalized_url": current_normalized_url,
                    "previous_canonical_hash": current_canonical_hash,
                    "resolved_url": next_url,
                    "resolved_normalized_url": next_normalized_url,
                    "resolved_canonical_hash": next_canonical_hash,
                    "resolver_reason": self._coerce_text(payload.get("reason")),
                    "redirect_hop_count": self._coerce_int(payload.get("redirect_hop_count")),
                }
            ),
        )
        outcome["status"] = "applied"
        outcome["resolved_url"] = next_url
        outcome["resolved_normalized_url"] = next_normalized_url
        outcome["resolved_canonical_hash"] = next_canonical_hash
        return outcome

    async def _materialize_extract_projection(
        self,
        *,
        conn: asyncpg.Connection,
        job_id: str,
        discovery_id: str,
        actor_module_db_id: str,
        result_json: dict[str, Any] | None,
    ) -> None:
        discovery = await conn.fetchrow(
            """
            select
              d.id::text as id,
              d.url,
              d.normalized_url,
              d.canonical_hash,
              d.title_hint,
              d.metadata,
              m.module_id as origin_module_id,
              m.trust_level::text as origin_module_trust_level
            from discoveries d
            left join modules m on m.id = d.origin_module_id
            where d.id = $1::uuid
            """,
            discovery_id,
        )
        if not discovery:
            return

        extraction = result_json if isinstance(result_json, dict) else {}
        posting_payload = extraction.get("posting")
        projection_payload = posting_payload if isinstance(posting_payload, dict) else extraction

        has_projection_signal = self._has_projection_signal(extraction=extraction, projection_payload=projection_payload)

        discovery_metadata = discovery["metadata"] if isinstance(discovery["metadata"], dict) else {}
        title = self._coerce_text(projection_payload.get("title")) or self._coerce_text(discovery["title_hint"])
        organization_name = self._coerce_text(projection_payload.get("organization_name")) or self._coerce_text(
            discovery_metadata.get("organization_name")
        )
        canonical_url = (
            self._coerce_text(projection_payload.get("canonical_url"))
            or self._coerce_text(projection_payload.get("url"))
            or self._coerce_text(discovery["url"])
            or self._coerce_text(discovery["normalized_url"])
        )
        normalized_url = (
            self._coerce_text(projection_payload.get("normalized_url"))
            or self._coerce_text(discovery["normalized_url"])
            or canonical_url
        )
        canonical_hash = self._coerce_text(projection_payload.get("canonical_hash")) or self._coerce_text(
            discovery["canonical_hash"]
        )
        dedupe_confidence = self._coerce_float(extraction.get("dedupe_confidence"))
        risk_flags = self._coerce_text_list(extraction.get("risk_flags"))
        country = self._coerce_text(projection_payload.get("country"))
        region = self._coerce_text(projection_payload.get("region"))
        city = self._coerce_text(projection_payload.get("city"))
        tags = self._coerce_text_list(projection_payload.get("tags"))
        areas = self._coerce_text_list(projection_payload.get("areas"))
        description_text = self._coerce_text(projection_payload.get("description_text"))
        application_url = self._coerce_text(projection_payload.get("application_url"))
        source_key_hint = self._resolve_source_key_hint(
            extraction=extraction,
            projection_payload=projection_payload,
            discovery_metadata=discovery_metadata,
        )
        origin_module_id = self._coerce_text(discovery["origin_module_id"]) or "unknown-module"
        origin_module_trust_level = self._coerce_text(discovery["origin_module_trust_level"]) or "untrusted"
        trust_policy = await self._resolve_source_trust_policy(
            conn=conn,
            source_key_hint=source_key_hint,
            module_id=origin_module_id,
            module_trust_level=origin_module_trust_level,
        )

        can_project_posting = bool(
            has_projection_signal and title and organization_name and canonical_url and normalized_url and canonical_hash
        )
        merge_policy = await self._evaluate_dedupe_merge_policy(
            conn=conn,
            extraction=extraction,
            projection_payload=projection_payload,
            canonical_hash=canonical_hash,
            normalized_url=normalized_url,
            canonical_url=canonical_url,
            application_url=application_url,
            title=title,
            organization_name=organization_name,
            description_text=description_text,
            tags=tags,
            areas=areas,
            country=country,
            region=region,
            city=city,
            can_project_posting=can_project_posting,
        )
        risk_flags = self._merge_risk_flags(risk_flags, merge_policy.risk_flags)
        (
            default_state,
            default_posting_status,
            trust_policy_payload,
        ) = self._resolve_publish_decision(
            can_project_posting=can_project_posting,
            trust_policy=trust_policy,
            dedupe_confidence=dedupe_confidence,
            risk_flags=risk_flags,
        )
        candidate_state = self._coerce_candidate_state(extraction.get("candidate_state"), default=default_state)
        if not can_project_posting and candidate_state == "published":
            candidate_state = "processed"
        if can_project_posting and candidate_state == "published" and default_state != "published":
            candidate_state = "needs_review"

        posting_status = (
            self._coerce_posting_status(projection_payload.get("status"), default=default_posting_status)
            if candidate_state == "published"
            else "archived"
        )
        persisted_candidate_state = candidate_state

        candidate_id = await conn.fetchval(
            """
            insert into posting_candidates (
              state,
              dedupe_bucket_key,
              dedupe_confidence,
              extracted_fields,
              risk_flags
            )
            values ($1::candidate_state, $2, $3, $4::jsonb, $5::text[])
            returning id::text
            """,
            candidate_state,
            canonical_hash,
            dedupe_confidence,
            json.dumps(extraction),
            risk_flags,
        )

        await conn.execute(
            """
            insert into candidate_discoveries (candidate_id, discovery_id)
            values ($1::uuid, $2::uuid)
            on conflict do nothing
            """,
            candidate_id,
            discovery_id,
        )
        await conn.execute(
            """
            insert into candidate_evidence (candidate_id, evidence_id)
            select $1::uuid, e.id
            from evidence e
            where e.discovery_id = $2::uuid
            on conflict do nothing
            """,
            candidate_id,
            discovery_id,
        )
        await conn.execute(
            """
            insert into provenance_events (
              entity_type,
              entity_id,
              event_type,
              actor_type,
              actor_id,
              payload
            )
            values ('posting_candidate', $1::uuid, 'materialized', 'machine', $2::uuid, $3::jsonb)
            """,
            candidate_id,
            actor_module_db_id,
            json.dumps({"job_id": job_id, "discovery_id": discovery_id, "state": candidate_state}),
        )

        merge_policy_payload: dict[str, Any] = {
            "merge_decision": merge_policy.decision,
            "merge_primary_candidate_id": merge_policy.primary_candidate_id,
            "merge_confidence": merge_policy.confidence,
            "merge_risk_flags": merge_policy.risk_flags,
            "merge_metadata": merge_policy.metadata,
        }
        skip_posting_projection = False
        if merge_policy.primary_candidate_id and merge_policy.decision == "auto_merged":
            try:
                await self._apply_candidate_merge(
                    conn=conn,
                    primary_candidate_id=merge_policy.primary_candidate_id,
                    secondary_candidate_id=candidate_id,
                    actor_type="machine",
                    actor_id=actor_module_db_id,
                    reason="dedupe scorer auto merge",
                    decision="auto_merged",
                    decided_by="machine_dedupe_v1",
                    confidence=merge_policy.confidence,
                    metadata={"source": "dedupe_scorer_v1", **merge_policy.metadata},
                )
                skip_posting_projection = True
            except (RepositoryConflictError, RepositoryNotFoundError):
                merge_policy_payload["merge_decision"] = "needs_review"
                merge_policy_payload["merge_risk_flags"] = self._merge_risk_flags(
                    merge_policy.risk_flags,
                    ["conflict_auto_merge_blocked"],
                )
                merge_policy_payload["merge_metadata"] = {
                    **merge_policy.metadata,
                    "auto_merge_blocked": True,
                }
                candidate_state = "needs_review"
                posting_status = "archived"
                await self._record_candidate_merge_decision(
                    conn=conn,
                    primary_candidate_id=merge_policy.primary_candidate_id,
                    secondary_candidate_id=candidate_id,
                    decision="needs_review",
                    confidence=merge_policy.confidence,
                    decided_by="machine_dedupe_v1",
                    rationale="auto merge blocked; queued for moderation",
                    metadata={"source": "dedupe_scorer_v1", **merge_policy_payload["merge_metadata"]},
                    actor_type="machine",
                    actor_id=actor_module_db_id,
                )
        elif merge_policy.primary_candidate_id and merge_policy.decision in {"needs_review", "rejected"}:
            await self._record_candidate_merge_decision(
                conn=conn,
                primary_candidate_id=merge_policy.primary_candidate_id,
                secondary_candidate_id=candidate_id,
                decision=merge_policy.decision,
                confidence=merge_policy.confidence,
                decided_by="machine_dedupe_v1",
                rationale="dedupe scorer routing",
                metadata={"source": "dedupe_scorer_v1", **merge_policy.metadata},
                    actor_type="machine",
                    actor_id=actor_module_db_id,
                )

        (
            candidate_state,
            posting_status,
            merge_policy_reason,
            moderation_route,
        ) = self._resolve_merge_decision_routing(
            trust_policy=trust_policy,
            merge_decision=self._coerce_text(merge_policy_payload["merge_decision"]) or "none",
            candidate_state=candidate_state,
            posting_status=posting_status,
        )
        if candidate_state != persisted_candidate_state:
            await conn.execute(
                """
                update posting_candidates
                set state = $2::candidate_state
                where id = $1::uuid
                """,
                candidate_id,
                candidate_state,
            )

        if merge_policy_reason:
            trust_policy_payload["reason"] = merge_policy_reason
        if moderation_route:
            trust_policy_payload["moderation_route"] = moderation_route
        trust_policy_payload.update(merge_policy_payload)

        await conn.execute(
            """
            insert into provenance_events (
              entity_type,
              entity_id,
              event_type,
              actor_type,
              actor_id,
              payload
            )
            values ('posting_candidate', $1::uuid, 'trust_policy_applied', 'machine', $2::uuid, $3::jsonb)
            """,
            candidate_id,
            actor_module_db_id,
            json.dumps(
                {
                    "job_id": job_id,
                    "discovery_id": discovery_id,
                    "candidate_state": candidate_state,
                    "posting_status": posting_status,
                    **trust_policy_payload,
                }
            ),
        )

        if not can_project_posting or skip_posting_projection:
            return

        source_refs = self._coerce_json_list(projection_payload.get("source_refs")) or [{"discovery_id": discovery_id}]
        deadline = self._coerce_datetime(projection_payload.get("deadline"))

        posting_id = await conn.fetchval(
            """
            insert into postings (
              candidate_id,
              title,
              canonical_url,
              normalized_url,
              canonical_hash,
              sector,
              degree_level,
              opportunity_kind,
              organization_name,
              country,
              region,
              city,
              remote,
              tags,
              areas,
              description_text,
              application_url,
              deadline,
              source_refs,
              status,
              published_at
            )
            values (
              $1::uuid,
              $2,
              $3,
              $4,
              $5,
              $6,
              $7,
              $8,
              $9,
              $10,
              $11,
              $12,
              $13,
              $14::text[],
              $15::text[],
              $16,
              $17,
              $18::timestamptz,
              $19::jsonb,
              $20::posting_status,
              case when $20::posting_status = 'active' then now() else null end
            )
            on conflict (canonical_hash)
            do update set
              candidate_id = excluded.candidate_id,
              title = excluded.title,
              canonical_url = excluded.canonical_url,
              normalized_url = excluded.normalized_url,
              sector = excluded.sector,
              degree_level = excluded.degree_level,
              opportunity_kind = excluded.opportunity_kind,
              organization_name = excluded.organization_name,
              country = excluded.country,
              region = excluded.region,
              city = excluded.city,
              remote = excluded.remote,
              tags = excluded.tags,
              areas = excluded.areas,
              description_text = excluded.description_text,
              application_url = excluded.application_url,
              deadline = excluded.deadline,
              source_refs = excluded.source_refs,
              status = excluded.status
            returning id::text
            """,
            candidate_id,
            title,
            canonical_url,
            normalized_url,
            canonical_hash,
            self._coerce_text(projection_payload.get("sector")),
            self._coerce_text(projection_payload.get("degree_level")),
            self._coerce_text(projection_payload.get("opportunity_kind")),
            organization_name,
            country,
            region,
            city,
            self._coerce_bool(projection_payload.get("remote")),
            tags,
            areas,
            description_text,
            application_url,
            deadline,
            json.dumps(source_refs),
            posting_status,
        )

        await conn.execute(
            """
            insert into provenance_events (
              entity_type,
              entity_id,
              event_type,
              actor_type,
              actor_id,
              payload
            )
            values ('posting', $1::uuid, 'projected', 'machine', $2::uuid, $3::jsonb)
            """,
            posting_id,
            actor_module_db_id,
            json.dumps({"job_id": job_id, "candidate_id": candidate_id, "discovery_id": discovery_id}),
        )

    async def list_candidates(
        self,
        limit: int,
        offset: int,
        state: str | None,
        source: str | None = None,
        age: str | None = None,
    ) -> list[dict[str, Any]]:
        normalized_source = self._coerce_text(source)
        normalized_age = self._coerce_text(age)
        if normalized_age and normalized_age not in QUEUE_AGE_BUCKETS:
            raise RepositoryValidationError("invalid candidate age bucket")
        pool = await self._get_pool()
        rows = await pool.fetch(
            """
            with discovery_rollup as (
              select
                cd.candidate_id,
                array_agg(distinct cd.discovery_id::text) as discovery_ids
              from candidate_discoveries cd
              group by cd.candidate_id
            ),
            source_rollup as (
              select
                cd.candidate_id,
                array_agg(
                  distinct coalesce(
                    nullif(trim(d.metadata->>'source_key'), ''),
                    nullif(trim(d.metadata->>'source'), ''),
                    nullif(trim(m.module_id), ''),
                    'unknown'
                  )
                ) as sources
              from candidate_discoveries cd
              join discoveries d on d.id = cd.discovery_id
              left join modules m on m.id = d.origin_module_id
              group by cd.candidate_id
            )
            select
              pc.id::text as id,
              pc.state::text as state,
              pc.dedupe_confidence,
              pc.risk_flags,
              pc.extracted_fields,
              coalesce(dr.discovery_ids, '{}') as discovery_ids,
              p.id::text as posting_id,
              pc.created_at,
              pc.updated_at
            from posting_candidates pc
            left join discovery_rollup dr on dr.candidate_id = pc.id
            left join source_rollup sr on sr.candidate_id = pc.id
            left join postings p on p.candidate_id = pc.id
            where ($3::text is null or pc.state::text = $3::text)
              and ($4::text is null or $4::text = any(coalesce(sr.sources, array['unknown']::text[])))
              and (
                $5::text is null
                or (
                  case
                    when now() - pc.updated_at < interval '24 hours' then 'lt_24h'
                    when now() - pc.updated_at < interval '72 hours' then 'd1_3'
                    when now() - pc.updated_at < interval '168 hours' then 'd3_7'
                    else 'gt_7d'
                  end
                ) = $5::text
              )
            order by pc.updated_at desc
            limit $1
            offset $2
            """,
            limit,
            offset,
            state,
            normalized_source,
            normalized_age,
        )
        return [self._candidate_row_to_dict(row) for row in rows]

    async def list_candidate_facets(
        self,
        *,
        state: str | None = None,
        source: str | None = None,
        age: str | None = None,
    ) -> dict[str, Any]:
        normalized_source = self._coerce_text(source)
        normalized_age = self._coerce_text(age)
        if normalized_age and normalized_age not in QUEUE_AGE_BUCKETS:
            raise RepositoryValidationError("invalid candidate age bucket")

        pool = await self._get_pool()
        facet_rows = await pool.fetch(
            """
            with source_rollup as (
              select
                cd.candidate_id,
                array_agg(
                  distinct coalesce(
                    nullif(trim(d.metadata->>'source_key'), ''),
                    nullif(trim(d.metadata->>'source'), ''),
                    nullif(trim(m.module_id), ''),
                    'unknown'
                  )
                ) as sources
              from candidate_discoveries cd
              join discoveries d on d.id = cd.discovery_id
              left join modules m on m.id = d.origin_module_id
              group by cd.candidate_id
            ),
            candidate_base as (
              select
                pc.id::text as id,
                pc.state::text as state,
                coalesce(sr.sources, array['unknown']::text[]) as sources,
                case
                  when now() - pc.updated_at < interval '24 hours' then 'lt_24h'
                  when now() - pc.updated_at < interval '72 hours' then 'd1_3'
                  when now() - pc.updated_at < interval '168 hours' then 'd3_7'
                  else 'gt_7d'
                end as age_bucket
              from posting_candidates pc
              left join source_rollup sr on sr.candidate_id = pc.id
              where ($1::text is null or pc.state::text = $1::text)
                and ($2::text is null or $2::text = any(coalesce(sr.sources, array['unknown']::text[])))
                and (
                  $3::text is null
                  or (
                    case
                      when now() - pc.updated_at < interval '24 hours' then 'lt_24h'
                      when now() - pc.updated_at < interval '72 hours' then 'd1_3'
                      when now() - pc.updated_at < interval '168 hours' then 'd3_7'
                      else 'gt_7d'
                    end
                  ) = $3::text
                )
            )
            select facet, value, count
            from (
              select
                'state'::text as facet,
                state as value,
                count(*)::int as count
              from candidate_base
              group by state
              union all
              select
                'source'::text as facet,
                source_value as value,
                count(distinct id)::int as count
              from candidate_base
              cross join unnest(sources) as source_value
              group by source_value
              union all
              select
                'age'::text as facet,
                age_bucket as value,
                count(*)::int as count
              from candidate_base
              group by age_bucket
            ) facets
            order by facet asc, count desc, value asc
            """,
            state,
            normalized_source,
            normalized_age,
        )

        states: list[dict[str, Any]] = []
        sources: list[dict[str, Any]] = []
        ages: list[dict[str, Any]] = []
        for row in facet_rows:
            item = {"value": row["value"], "count": int(row["count"])}
            facet = row["facet"]
            if facet == "state":
                states.append(item)
            elif facet == "source":
                sources.append(item)
            elif facet == "age":
                ages.append(item)

        return {
            "total": sum(item["count"] for item in states),
            "states": states,
            "sources": sources,
            "ages": ages,
        }

    async def list_candidate_events(self, *, candidate_id: str, limit: int, offset: int) -> list[dict[str, Any]]:
        pool = await self._get_pool()
        try:
            async with pool.acquire() as conn:
                exists = await conn.fetchval(
                    """
                    select 1
                    from posting_candidates
                    where id = $1::uuid
                    """,
                    candidate_id,
                )
                if not exists:
                    raise RepositoryNotFoundError("candidate not found")
                rows = await conn.fetch(
                    """
                    with candidate_postings as (
                      select id
                      from postings
                      where candidate_id = $1::uuid
                    )
                    select
                      id,
                      entity_type,
                      entity_id::text as entity_id,
                      event_type,
                      actor_type,
                      actor_id::text as actor_id,
                      payload,
                      created_at
                    from provenance_events
                    where (entity_type = 'posting_candidate' and entity_id = $1::uuid)
                      or (entity_type = 'posting' and entity_id in (select id from candidate_postings))
                    order by created_at desc, id desc
                    limit $2
                    offset $3
                    """,
                    candidate_id,
                    limit,
                    offset,
                )
                return [self._candidate_event_row_to_dict(row) for row in rows]
        except (pg_exc.InvalidTextRepresentationError, asyncpg.DataError) as exc:
            raise RepositoryConflictError("invalid candidate id") from exc

    async def update_candidate_state(
        self,
        *,
        candidate_id: str,
        state: str,
        actor_user_id: str,
        reason: str | None,
    ) -> dict[str, Any]:
        pool = await self._get_pool()

        try:
            async with pool.acquire() as conn:
                async with conn.transaction():
                    existing = await conn.fetchrow(
                        """
                        select
                          id::text as id,
                          state::text as state
                        from posting_candidates
                        where id = $1::uuid
                        for update
                        """,
                        candidate_id,
                    )
                    if not existing:
                        raise RepositoryNotFoundError("candidate not found")

                    from_state = str(existing["state"])
                    if state != from_state:
                        self._validate_candidate_transition(from_state=from_state, to_state=state)

                    if state == "published":
                        has_posting = await conn.fetchval(
                            """
                            select 1
                            from postings
                            where candidate_id = $1::uuid
                            limit 1
                            """,
                            candidate_id,
                        )
                        if not has_posting:
                            raise RepositoryConflictError("cannot publish candidate without posting projection")

                    await conn.execute(
                        """
                        update posting_candidates
                        set state = $2::candidate_state
                        where id = $1::uuid
                        """,
                        candidate_id,
                        state,
                    )

                    posting_status = self._derive_posting_status_for_candidate_state(state)
                    if posting_status:
                        await conn.execute(
                            """
                            update postings
                            set
                              status = $2::posting_status,
                              published_at = case
                                when $2::posting_status = 'active' then coalesce(published_at, now())
                                else published_at
                              end
                            where candidate_id = $1::uuid
                            """,
                            candidate_id,
                            posting_status,
                        )

                    row = await self._fetch_candidate_row(conn=conn, candidate_id=candidate_id)
                    await conn.execute(
                        """
                        insert into provenance_events (
                          entity_type,
                          entity_id,
                          event_type,
                          actor_type,
                          actor_id,
                          payload
                        )
                        values ('posting_candidate', $1::uuid, 'state_changed', 'human', $2::uuid, $3::jsonb)
                        """,
                        candidate_id,
                        actor_user_id,
                        json.dumps(
                            {
                                "from_state": from_state,
                                "to_state": state,
                                "reason": reason,
                            }
                        ),
                    )
                    if posting_status:
                        posting_id = row["posting_id"] if row else None
                        if posting_id:
                            await conn.execute(
                                """
                                insert into provenance_events (
                                  entity_type,
                                  entity_id,
                                  event_type,
                                  actor_type,
                                  actor_id,
                                  payload
                                )
                                values ('posting', $1::uuid, 'state_changed', 'human', $2::uuid, $3::jsonb)
                                """,
                                posting_id,
                                actor_user_id,
                                json.dumps({"candidate_state": state, "posting_status": posting_status}),
                            )

                    if not row:
                        raise RepositoryNotFoundError("candidate not found")
                    return self._candidate_row_to_dict(row)
        except (pg_exc.InvalidTextRepresentationError, asyncpg.DataError) as exc:
            raise RepositoryConflictError("invalid candidate state or id") from exc

    async def override_candidate_state(
        self,
        *,
        candidate_id: str,
        state: str,
        actor_user_id: str,
        reason: str | None,
        posting_status: str | None,
    ) -> dict[str, Any]:
        pool = await self._get_pool()

        try:
            async with pool.acquire() as conn:
                async with conn.transaction():
                    existing = await conn.fetchrow(
                        """
                        select
                          id::text as id,
                          state::text as state
                        from posting_candidates
                        where id = $1::uuid
                        for update
                        """,
                        candidate_id,
                    )
                    if not existing:
                        raise RepositoryNotFoundError("candidate not found")

                    has_posting = await conn.fetchval(
                        """
                        select 1
                        from postings
                        where candidate_id = $1::uuid
                        limit 1
                        """,
                        candidate_id,
                    )
                    if state == "published" and not has_posting:
                        raise RepositoryConflictError("cannot publish candidate without posting projection")

                    await conn.execute(
                        """
                        update posting_candidates
                        set state = $2::candidate_state
                        where id = $1::uuid
                        """,
                        candidate_id,
                        state,
                    )

                    resolved_posting_status = posting_status or self._derive_posting_status_for_candidate_state(state)
                    if resolved_posting_status:
                        await conn.execute(
                            """
                            update postings
                            set
                              status = $2::posting_status,
                              published_at = case
                                when $2::posting_status = 'active' then coalesce(published_at, now())
                                else published_at
                              end
                            where candidate_id = $1::uuid
                            """,
                            candidate_id,
                            resolved_posting_status,
                        )

                    row = await self._fetch_candidate_row(conn=conn, candidate_id=candidate_id)
                    await conn.execute(
                        """
                        insert into provenance_events (
                          entity_type,
                          entity_id,
                          event_type,
                          actor_type,
                          actor_id,
                          payload
                        )
                        values ('posting_candidate', $1::uuid, 'state_overridden', 'human', $2::uuid, $3::jsonb)
                        """,
                        candidate_id,
                        actor_user_id,
                        json.dumps(
                            {
                                "from_state": str(existing["state"]),
                                "to_state": state,
                                "reason": reason,
                                "posting_status": resolved_posting_status,
                            }
                        ),
                    )
                    if resolved_posting_status and row and row["posting_id"]:
                        await conn.execute(
                            """
                            insert into provenance_events (
                              entity_type,
                              entity_id,
                              event_type,
                              actor_type,
                              actor_id,
                              payload
                            )
                            values ('posting', $1::uuid, 'state_overridden', 'human', $2::uuid, $3::jsonb)
                            """,
                            row["posting_id"],
                            actor_user_id,
                            json.dumps({"candidate_state": state, "posting_status": resolved_posting_status}),
                        )

                    if not row:
                        raise RepositoryNotFoundError("candidate not found")
                    return self._candidate_row_to_dict(row)
        except (pg_exc.InvalidTextRepresentationError, asyncpg.DataError) as exc:
            raise RepositoryConflictError("invalid candidate state or id") from exc

    async def merge_candidates(
        self,
        *,
        primary_candidate_id: str,
        secondary_candidate_id: str,
        actor_user_id: str,
        reason: str | None,
    ) -> dict[str, Any]:
        pool = await self._get_pool()
        try:
            async with pool.acquire() as conn:
                async with conn.transaction():
                    return await self._apply_candidate_merge(
                        conn=conn,
                        primary_candidate_id=primary_candidate_id,
                        secondary_candidate_id=secondary_candidate_id,
                        actor_type="human",
                        actor_id=actor_user_id,
                        reason=reason,
                        decision="manual_merged",
                        decided_by="human_moderator",
                        confidence=None,
                        metadata={"actor_user_id": actor_user_id},
                    )
        except (pg_exc.InvalidTextRepresentationError, asyncpg.DataError) as exc:
            raise RepositoryConflictError("invalid candidate id") from exc

    async def _apply_candidate_merge(
        self,
        *,
        conn: asyncpg.Connection,
        primary_candidate_id: str,
        secondary_candidate_id: str,
        actor_type: str,
        actor_id: str,
        reason: str | None,
        decision: str,
        decided_by: str,
        confidence: float | None,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        if primary_candidate_id == secondary_candidate_id:
            raise RepositoryConflictError("primary and secondary candidate ids must differ")

        locked_rows = await conn.fetch(
            """
            select
              id::text as id
            from posting_candidates
            where id = any(array[$1::uuid, $2::uuid])
            order by id
            for update
            """,
            primary_candidate_id,
            secondary_candidate_id,
        )
        if len(locked_rows) != 2:
            raise RepositoryNotFoundError("candidate not found")

        primary_posting_id = await conn.fetchval(
            """
            select id::text
            from postings
            where candidate_id = $1::uuid
            """,
            primary_candidate_id,
        )
        secondary_posting_id = await conn.fetchval(
            """
            select id::text
            from postings
            where candidate_id = $1::uuid
            """,
            secondary_candidate_id,
        )
        if primary_posting_id and secondary_posting_id and primary_posting_id != secondary_posting_id:
            raise RepositoryConflictError("cannot merge candidates that both already have postings")

        await conn.execute(
            """
            insert into candidate_discoveries (candidate_id, discovery_id)
            select $1::uuid, discovery_id
            from candidate_discoveries
            where candidate_id = $2::uuid
            on conflict do nothing
            """,
            primary_candidate_id,
            secondary_candidate_id,
        )
        await conn.execute(
            """
            insert into candidate_evidence (candidate_id, evidence_id)
            select $1::uuid, evidence_id
            from candidate_evidence
            where candidate_id = $2::uuid
            on conflict do nothing
            """,
            primary_candidate_id,
            secondary_candidate_id,
        )

        moved_posting_id: str | None = None
        if not primary_posting_id and secondary_posting_id:
            await conn.execute(
                """
                update postings
                set candidate_id = $1::uuid
                where id = $2::uuid
                """,
                primary_candidate_id,
                secondary_posting_id,
            )
            moved_posting_id = secondary_posting_id

        await conn.execute(
            """
            update posting_candidates
            set state = 'archived'
            where id = $1::uuid
            """,
            secondary_candidate_id,
        )

        await self._record_candidate_merge_decision(
            conn=conn,
            primary_candidate_id=primary_candidate_id,
            secondary_candidate_id=secondary_candidate_id,
            decision=decision,
            confidence=confidence,
            decided_by=decided_by,
            rationale=reason,
            metadata=metadata,
            actor_type=actor_type,
            actor_id=actor_id,
        )

        await conn.execute(
            """
            insert into provenance_events (
              entity_type,
              entity_id,
              event_type,
              actor_type,
              actor_id,
              payload
            )
            values ('posting_candidate', $1::uuid, 'merge_applied', $2, $3::uuid, $4::jsonb)
            """,
            primary_candidate_id,
            actor_type,
            actor_id,
            json.dumps({"secondary_candidate_id": secondary_candidate_id, "reason": reason, "decision": decision}),
        )
        await conn.execute(
            """
            insert into provenance_events (
              entity_type,
              entity_id,
              event_type,
              actor_type,
              actor_id,
              payload
            )
            values ('posting_candidate', $1::uuid, 'merged_away', $2, $3::uuid, $4::jsonb)
            """,
            secondary_candidate_id,
            actor_type,
            actor_id,
            json.dumps({"primary_candidate_id": primary_candidate_id, "reason": reason, "decision": decision}),
        )
        if moved_posting_id:
            await conn.execute(
                """
                insert into provenance_events (
                  entity_type,
                  entity_id,
                  event_type,
                  actor_type,
                  actor_id,
                  payload
                )
                values ('posting', $1::uuid, 'candidate_reassigned', $2, $3::uuid, $4::jsonb)
                """,
                moved_posting_id,
                actor_type,
                actor_id,
                json.dumps(
                    {
                        "from_candidate_id": secondary_candidate_id,
                        "to_candidate_id": primary_candidate_id,
                        "reason": reason,
                        "decision": decision,
                    }
                ),
            )

        row = await self._fetch_candidate_row(conn=conn, candidate_id=primary_candidate_id)
        if not row:
            raise RepositoryNotFoundError("candidate not found")
        return self._candidate_row_to_dict(row)

    async def _record_candidate_merge_decision(
        self,
        *,
        conn: asyncpg.Connection,
        primary_candidate_id: str,
        secondary_candidate_id: str,
        decision: str,
        confidence: float | None,
        decided_by: str,
        rationale: str | None,
        metadata: dict[str, Any],
        actor_type: str,
        actor_id: str,
    ) -> None:
        await conn.execute(
            """
            insert into candidate_merge_decisions (
              primary_candidate_id,
              secondary_candidate_id,
              decision,
              confidence,
              decided_by,
              rationale,
              metadata
            )
            values ($1::uuid, $2::uuid, $3::merge_decision, $4, $5, $6, $7::jsonb)
            on conflict (primary_candidate_id, secondary_candidate_id)
            do update set
              decision = excluded.decision,
              confidence = excluded.confidence,
              decided_by = excluded.decided_by,
              rationale = excluded.rationale,
              metadata = excluded.metadata
            """,
            primary_candidate_id,
            secondary_candidate_id,
            decision,
            round(confidence, 4) if confidence is not None else None,
            decided_by,
            rationale,
            json.dumps(metadata),
        )
        await conn.execute(
            """
            insert into provenance_events (
              entity_type,
              entity_id,
              event_type,
              actor_type,
              actor_id,
              payload
            )
            values ('posting_candidate', $1::uuid, 'merge_decision_recorded', $2, $3::uuid, $4::jsonb)
            """,
            secondary_candidate_id,
            actor_type,
            actor_id,
            json.dumps(
                {
                    "primary_candidate_id": primary_candidate_id,
                    "secondary_candidate_id": secondary_candidate_id,
                    "decision": decision,
                    "confidence": round(confidence, 4) if confidence is not None else None,
                    "decided_by": decided_by,
                    "rationale": rationale,
                    "metadata": metadata,
                }
            ),
        )

    async def _record_source_trust_policy_event(
        self,
        *,
        conn: asyncpg.Connection,
        policy_id: str,
        event_type: str,
        actor_user_id: str,
        payload: dict[str, Any],
    ) -> None:
        await conn.execute(
            """
            insert into provenance_events (
              entity_type,
              entity_id,
              event_type,
              actor_type,
              actor_id,
              payload
            )
            values ('source_trust_policy', $1::uuid, $2, 'human', $3::uuid, $4::jsonb)
            """,
            policy_id,
            event_type,
            actor_user_id,
            json.dumps(payload),
        )

    async def list_source_trust_policies(
        self,
        *,
        source_key: str | None,
        enabled: bool | None,
        trust_level: str | None,
        limit: int,
        offset: int,
    ) -> list[dict[str, Any]]:
        pool = await self._get_pool()

        normalized_source_key = self._coerce_text(source_key)
        normalized_trust_level = self._coerce_text(trust_level)
        if normalized_trust_level and normalized_trust_level not in SOURCE_POLICY_TRUST_LEVELS:
            raise RepositoryValidationError(
                "trust_level must be one of: trusted, semi_trusted, untrusted",
            )

        rows = await pool.fetch(
            """
            select
              source_key,
              trust_level::text as trust_level,
              auto_publish,
              requires_moderation,
              rules_json,
              enabled,
              created_at,
              updated_at
            from source_trust_policy
            where ($1::text is null or source_key = $1)
              and ($2::boolean is null or enabled = $2)
              and ($3::text is null or trust_level::text = $3)
            order by source_key asc
            limit $4
            offset $5
            """,
            normalized_source_key,
            enabled,
            normalized_trust_level,
            limit,
            offset,
        )
        return [self._source_trust_policy_row_to_dict(row) for row in rows]

    async def get_source_trust_policy(self, *, source_key: str) -> dict[str, Any]:
        pool = await self._get_pool()

        normalized_source_key = self._coerce_text(source_key)
        if not normalized_source_key:
            raise RepositoryValidationError("source_key must be a non-empty string")

        row = await pool.fetchrow(
            """
            select
              source_key,
              trust_level::text as trust_level,
              auto_publish,
              requires_moderation,
              rules_json,
              enabled,
              created_at,
              updated_at
            from source_trust_policy
            where source_key = $1
            """,
            normalized_source_key,
        )
        if not row:
            raise RepositoryNotFoundError("source trust policy not found")
        return self._source_trust_policy_row_to_dict(row)

    async def set_source_trust_policy_enabled(
        self,
        *,
        source_key: str,
        enabled: bool,
        actor_user_id: str | None = None,
    ) -> dict[str, Any]:
        pool = await self._get_pool()

        normalized_source_key = self._coerce_text(source_key)
        if not normalized_source_key:
            raise RepositoryValidationError("source_key must be a non-empty string")
        normalized_actor_user_id = self._coerce_text(actor_user_id)

        async with pool.acquire() as conn:
            async with conn.transaction():
                previous_row = await conn.fetchrow(
                    """
                    select
                      id::text as id,
                      source_key,
                      enabled
                    from source_trust_policy
                    where source_key = $1
                    for update
                    """,
                    normalized_source_key,
                )
                if not previous_row:
                    raise RepositoryNotFoundError("source trust policy not found")

                row = await conn.fetchrow(
                    """
                    update source_trust_policy
                    set enabled = $2
                    where source_key = $1
                    returning
                      id::text as id,
                      source_key,
                      trust_level::text as trust_level,
                      auto_publish,
                      requires_moderation,
                      rules_json,
                      enabled,
                      created_at,
                      updated_at
                    """,
                    normalized_source_key,
                    bool(enabled),
                )
                if not row:
                    raise RepositoryNotFoundError("source trust policy not found")

                if normalized_actor_user_id:
                    await self._record_source_trust_policy_event(
                        conn=conn,
                        policy_id=row["id"],
                        event_type="policy_enabled_changed",
                        actor_user_id=normalized_actor_user_id,
                        payload={
                            "source_key": row["source_key"],
                            "previous_enabled": bool(previous_row["enabled"]),
                            "enabled": bool(row["enabled"]),
                        },
                    )
                return self._source_trust_policy_row_to_dict(row)

    async def _record_url_normalization_override_event(
        self,
        *,
        conn: asyncpg.Connection,
        override_id: str,
        event_type: str,
        actor_user_id: str,
        payload: dict[str, Any],
    ) -> None:
        await conn.execute(
            """
            insert into provenance_events (
              entity_type,
              entity_id,
              event_type,
              actor_type,
              actor_id,
              payload
            )
            values ('url_normalization_override', $1::uuid, $2, 'human', $3::uuid, $4::jsonb)
            """,
            override_id,
            event_type,
            actor_user_id,
            json.dumps(payload),
        )

    async def list_url_normalization_overrides(
        self,
        *,
        domain: str | None,
        enabled: bool | None,
        limit: int,
        offset: int,
    ) -> list[dict[str, Any]]:
        pool = await self._get_pool()
        normalized_domain = self._normalize_url_override_domain(domain, field_path="domain", allow_none=True)
        rows = await pool.fetch(
            """
            select
              id::text as id,
              domain,
              strip_query_params,
              strip_query_prefixes,
              strip_www,
              force_https,
              enabled,
              created_at,
              updated_at
            from url_normalization_overrides
            where ($1::text is null or domain = $1)
              and ($2::boolean is null or enabled = $2)
            order by domain asc
            limit $3
            offset $4
            """,
            normalized_domain,
            enabled,
            limit,
            offset,
        )
        return [self._url_normalization_override_row_to_dict(row) for row in rows]

    async def get_url_normalization_override(self, *, domain: str) -> dict[str, Any]:
        pool = await self._get_pool()
        normalized_domain = self._normalize_url_override_domain(domain, field_path="domain")
        row = await pool.fetchrow(
            """
            select
              id::text as id,
              domain,
              strip_query_params,
              strip_query_prefixes,
              strip_www,
              force_https,
              enabled,
              created_at,
              updated_at
            from url_normalization_overrides
            where domain = $1
            """,
            normalized_domain,
        )
        if not row:
            raise RepositoryNotFoundError("url normalization override not found")
        return self._url_normalization_override_row_to_dict(row)

    async def upsert_url_normalization_override(
        self,
        *,
        domain: str,
        strip_query_params: Any,
        strip_query_prefixes: Any,
        strip_www: bool,
        force_https: bool,
        enabled: bool = True,
        actor_user_id: str | None = None,
    ) -> dict[str, Any]:
        pool = await self._get_pool()

        normalized_domain = self._normalize_url_override_domain(domain, field_path="domain")
        normalized_strip_query_params = self._normalize_url_override_tokens(
            strip_query_params,
            field_path="strip_query_params",
            strict=True,
        )
        normalized_strip_query_prefixes = self._normalize_url_override_tokens(
            strip_query_prefixes,
            field_path="strip_query_prefixes",
            strict=True,
        )
        normalized_actor_user_id = self._coerce_text(actor_user_id)

        async with pool.acquire() as conn:
            async with conn.transaction():
                existing_row = await conn.fetchrow(
                    """
                    select
                      id::text as id,
                      domain,
                      strip_query_params,
                      strip_query_prefixes,
                      strip_www,
                      force_https,
                      enabled
                    from url_normalization_overrides
                    where domain = $1
                    for update
                    """,
                    normalized_domain,
                )
                if existing_row:
                    row = await conn.fetchrow(
                        """
                        update url_normalization_overrides
                        set
                          strip_query_params = $2::text[],
                          strip_query_prefixes = $3::text[],
                          strip_www = $4,
                          force_https = $5,
                          enabled = $6
                        where domain = $1
                        returning
                          id::text as id,
                          domain,
                          strip_query_params,
                          strip_query_prefixes,
                          strip_www,
                          force_https,
                          enabled,
                          created_at,
                          updated_at
                        """,
                        normalized_domain,
                        normalized_strip_query_params,
                        normalized_strip_query_prefixes,
                        bool(strip_www),
                        bool(force_https),
                        bool(enabled),
                    )
                    operation = "updated"
                else:
                    row = await conn.fetchrow(
                        """
                        insert into url_normalization_overrides (
                          domain,
                          strip_query_params,
                          strip_query_prefixes,
                          strip_www,
                          force_https,
                          enabled
                        )
                        values ($1, $2::text[], $3::text[], $4, $5, $6)
                        returning
                          id::text as id,
                          domain,
                          strip_query_params,
                          strip_query_prefixes,
                          strip_www,
                          force_https,
                          enabled,
                          created_at,
                          updated_at
                        """,
                        normalized_domain,
                        normalized_strip_query_params,
                        normalized_strip_query_prefixes,
                        bool(strip_www),
                        bool(force_https),
                        bool(enabled),
                    )
                    operation = "created"
                if not row:
                    raise RepositoryConflictError("failed to upsert url normalization override")

                if normalized_actor_user_id:
                    previous_payload: dict[str, Any] | None = None
                    if existing_row:
                        previous_payload = {
                            "domain": existing_row["domain"],
                            "strip_query_params": self._normalize_url_override_tokens(
                                existing_row["strip_query_params"],
                                field_path="strip_query_params",
                                strict=False,
                            ),
                            "strip_query_prefixes": self._normalize_url_override_tokens(
                                existing_row["strip_query_prefixes"],
                                field_path="strip_query_prefixes",
                                strict=False,
                            ),
                            "strip_www": bool(existing_row["strip_www"]),
                            "force_https": bool(existing_row["force_https"]),
                            "enabled": bool(existing_row["enabled"]),
                        }
                    await self._record_url_normalization_override_event(
                        conn=conn,
                        override_id=row["id"],
                        event_type="override_upserted",
                        actor_user_id=normalized_actor_user_id,
                        payload={
                            "domain": row["domain"],
                            "operation": operation,
                            "strip_query_params": self._normalize_url_override_tokens(
                                row["strip_query_params"],
                                field_path="strip_query_params",
                                strict=False,
                            ),
                            "strip_query_prefixes": self._normalize_url_override_tokens(
                                row["strip_query_prefixes"],
                                field_path="strip_query_prefixes",
                                strict=False,
                            ),
                            "strip_www": bool(row["strip_www"]),
                            "force_https": bool(row["force_https"]),
                            "enabled": bool(row["enabled"]),
                            "previous": previous_payload,
                        },
                    )

                return self._url_normalization_override_row_to_dict(row)

    async def set_url_normalization_override_enabled(
        self,
        *,
        domain: str,
        enabled: bool,
        actor_user_id: str | None = None,
    ) -> dict[str, Any]:
        pool = await self._get_pool()
        normalized_domain = self._normalize_url_override_domain(domain, field_path="domain")
        normalized_actor_user_id = self._coerce_text(actor_user_id)

        async with pool.acquire() as conn:
            async with conn.transaction():
                previous_row = await conn.fetchrow(
                    """
                    select
                      id::text as id,
                      domain,
                      enabled
                    from url_normalization_overrides
                    where domain = $1
                    for update
                    """,
                    normalized_domain,
                )
                if not previous_row:
                    raise RepositoryNotFoundError("url normalization override not found")

                row = await conn.fetchrow(
                    """
                    update url_normalization_overrides
                    set enabled = $2
                    where domain = $1
                    returning
                      id::text as id,
                      domain,
                      strip_query_params,
                      strip_query_prefixes,
                      strip_www,
                      force_https,
                      enabled,
                      created_at,
                      updated_at
                    """,
                    normalized_domain,
                    bool(enabled),
                )
                if not row:
                    raise RepositoryNotFoundError("url normalization override not found")

                if normalized_actor_user_id:
                    await self._record_url_normalization_override_event(
                        conn=conn,
                        override_id=row["id"],
                        event_type="override_enabled_changed",
                        actor_user_id=normalized_actor_user_id,
                        payload={
                            "domain": row["domain"],
                            "previous_enabled": bool(previous_row["enabled"]),
                            "enabled": bool(row["enabled"]),
                        },
                    )

                return self._url_normalization_override_row_to_dict(row)

    async def list_enabled_url_normalization_overrides(self) -> dict[str, dict[str, Any]]:
        pool = await self._get_pool()
        rows = await pool.fetch(
            """
            select
              domain,
              strip_query_params,
              strip_query_prefixes,
              strip_www,
              force_https
            from url_normalization_overrides
            where enabled = true
            order by domain asc
            """,
        )
        return self._build_url_normalization_override_rules(rows)

    async def get_enabled_url_normalization_overrides_json(self) -> str | None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            return await self._fetch_enabled_url_normalization_overrides_json(conn=conn)

    async def list_modules(
        self,
        *,
        module_id: str | None,
        kind: str | None,
        enabled: bool | None,
        limit: int,
        offset: int,
    ) -> list[dict[str, Any]]:
        pool = await self._get_pool()

        normalized_module_id = self._coerce_text(module_id)
        normalized_kind = self._coerce_text(kind)
        if normalized_kind and normalized_kind not in MODULE_KINDS:
            raise RepositoryValidationError("kind must be one of: connector, processor")

        rows = await pool.fetch(
            """
            select
              id::text as id,
              module_id,
              name,
              kind::text as kind,
              enabled,
              scopes,
              trust_level::text as trust_level,
              created_at,
              updated_at
            from modules
            where ($1::text is null or module_id = $1)
              and ($2::text is null or kind::text = $2)
              and ($3::boolean is null or enabled = $3)
            order by updated_at desc, module_id asc
            limit $4
            offset $5
            """,
            normalized_module_id,
            normalized_kind,
            enabled,
            limit,
            offset,
        )
        return [self._module_row_to_dict(row) for row in rows]

    async def set_module_enabled(
        self,
        *,
        module_id: str,
        enabled: bool,
        actor_user_id: str | None = None,
    ) -> dict[str, Any]:
        pool = await self._get_pool()

        normalized_module_id = self._coerce_text(module_id)
        if not normalized_module_id:
            raise RepositoryValidationError("module_id must be a non-empty string")
        normalized_actor_user_id = self._coerce_text(actor_user_id)

        async with pool.acquire() as conn:
            async with conn.transaction():
                previous_row = await conn.fetchrow(
                    """
                    select
                      id::text as id,
                      module_id,
                      enabled
                    from modules
                    where module_id = $1
                    for update
                    """,
                    normalized_module_id,
                )
                if not previous_row:
                    raise RepositoryNotFoundError("module not found")

                row = await conn.fetchrow(
                    """
                    update modules
                    set enabled = $2
                    where module_id = $1
                    returning
                      id::text as id,
                      module_id,
                      name,
                      kind::text as kind,
                      enabled,
                      scopes,
                      trust_level::text as trust_level,
                      created_at,
                      updated_at
                    """,
                    normalized_module_id,
                    bool(enabled),
                )
                if not row:
                    raise RepositoryNotFoundError("module not found")

                if normalized_actor_user_id:
                    await conn.execute(
                        """
                        insert into provenance_events (
                          entity_type,
                          entity_id,
                          event_type,
                          actor_type,
                          actor_id,
                          payload
                        )
                        values ('module', $1::uuid, 'module_enabled_changed', 'human', $2::uuid, $3::jsonb)
                        """,
                        row["id"],
                        normalized_actor_user_id,
                        json.dumps(
                            {
                                "module_id": row["module_id"],
                                "previous_enabled": bool(previous_row["enabled"]),
                                "enabled": bool(row["enabled"]),
                            }
                        ),
                    )

                return self._module_row_to_dict(row)

    async def list_admin_jobs(
        self,
        *,
        status: str | None,
        kind: str | None,
        target_type: str | None,
        limit: int,
        offset: int,
    ) -> list[dict[str, Any]]:
        pool = await self._get_pool()

        normalized_status = self._coerce_text(status)
        if normalized_status and normalized_status not in ADMIN_JOB_FILTER_STATUSES:
            raise RepositoryValidationError("status must be one of: queued, claimed, done, failed")

        normalized_kind = self._coerce_text(kind)
        if normalized_kind and normalized_kind not in ADMIN_JOB_FILTER_KINDS:
            raise RepositoryValidationError(
                "kind must be one of: extract, check_freshness, resolve_url_redirects",
            )

        normalized_target_type = self._coerce_text(target_type)

        rows = await pool.fetch(
            """
            select
              id::text as id,
              kind::text as kind,
              target_type,
              target_id::text as target_id,
              status::text as status,
              attempt,
              locked_by_module_id::text as locked_by_module_id,
              lease_expires_at,
              next_run_at,
              inputs_json,
              result_json,
              error_json,
              created_at,
              updated_at
            from jobs
            where ($1::text is null or status::text = $1)
              and ($2::text is null or kind::text = $2)
              and ($3::text is null or target_type = $3)
            order by updated_at desc, id desc
            limit $4
            offset $5
            """,
            normalized_status,
            normalized_kind,
            normalized_target_type,
            limit,
            offset,
        )
        return [self._admin_job_row_to_dict(row) for row in rows]

    async def list_postings(
        self,
        *,
        limit: int,
        offset: int,
        q: str | None,
        organization_name: str | None,
        country: str | None,
        remote: bool | None,
        status: str | None,
        tag: str | None,
        sort_by: str,
        sort_dir: str,
    ) -> list[dict[str, Any]]:
        pool = await self._get_pool()
        conditions: list[str] = []
        params: list[Any] = []
        relevance_rank_sql: str | None = None

        def bind(value: Any) -> str:
            params.append(value)
            return f"${len(params)}"

        normalized_q = self._coerce_text(q)
        if normalized_q:
            token = bind(f"%{normalized_q}%")
            conditions.append(
                f"(p.title ilike {token} or p.organization_name ilike {token} or coalesce(p.description_text, '') ilike {token})"
            )
            normalized_q_lower = normalized_q.lower()
            exact_token = bind(normalized_q_lower)
            prefix_token = bind(f"{normalized_q_lower}%")
            contains_token = bind(f"%{normalized_q_lower}%")
            relevance_rank_sql = (
                "case "
                f"when lower(p.title) = {exact_token} then 600 "
                f"when lower(p.title) like {prefix_token} then 500 "
                f"when lower(p.title) like {contains_token} then 400 "
                f"when lower(p.organization_name) = {exact_token} then 300 "
                f"when lower(p.organization_name) like {prefix_token} then 250 "
                f"when lower(p.organization_name) like {contains_token} then 200 "
                f"when lower(coalesce(p.description_text, '')) like {contains_token} then 100 "
                "else 0 end"
            )

        normalized_org = self._coerce_text(organization_name)
        if normalized_org:
            conditions.append(f"p.organization_name ilike {bind(f'%{normalized_org}%')}")

        normalized_country = self._coerce_text(country)
        if normalized_country:
            conditions.append(f"p.country ilike {bind(normalized_country)}")

        if remote is not None:
            conditions.append(f"p.remote = {bind(remote)}")
        if status:
            conditions.append(f"p.status = {bind(status)}::posting_status")

        normalized_tag = self._coerce_text(tag)
        if normalized_tag:
            token = bind(normalized_tag)
            conditions.append(
                f"exists (select 1 from unnest(p.tags) as posting_tag(tag) where lower(posting_tag.tag) = lower({token}))"
            )

        where_sql = " and ".join(conditions) if conditions else "true"
        sort_expr = self._resolve_postings_sort_expr(sort_by)
        direction = "asc" if sort_dir == "asc" else "desc"
        tie_break_sql = "p.id asc" if sort_by == "created_at" else f"p.created_at {direction}, p.id asc"
        if sort_by in {"deadline", "published_at"}:
            order_by_sql = f"({sort_expr} is null) asc, {sort_expr} {direction}, {tie_break_sql}"
        else:
            order_by_sql = f"{sort_expr} {direction}, {tie_break_sql}"
        if relevance_rank_sql is not None:
            order_by_sql = f"{relevance_rank_sql} desc, {order_by_sql}"

        limit_token = bind(limit)
        offset_token = bind(offset)

        rows = await pool.fetch(
            f"""
            select
              id::text as id,
              title,
              organization_name,
              canonical_url,
              status::text as status,
              country,
              remote,
              tags,
              updated_at,
              created_at
            from postings p
            where {where_sql}
            order by {order_by_sql}
            limit {limit_token}
            offset {offset_token}
            """,
            *params,
        )
        return [self._posting_list_row_to_dict(row) for row in rows]

    def _source_trust_policy_row_to_dict(self, row: asyncpg.Record) -> dict[str, Any]:
        return {
            "source_key": row["source_key"],
            "trust_level": row["trust_level"],
            "auto_publish": bool(row["auto_publish"]),
            "requires_moderation": bool(row["requires_moderation"]),
            "rules_json": self._validate_source_trust_policy_rules_json(row["rules_json"], strict=False),
            "enabled": bool(row["enabled"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def _url_normalization_override_row_to_dict(self, row: asyncpg.Record) -> dict[str, Any]:
        return {
            "domain": row["domain"],
            "strip_query_params": self._normalize_url_override_tokens(
                row["strip_query_params"],
                field_path="strip_query_params",
                strict=False,
            ),
            "strip_query_prefixes": self._normalize_url_override_tokens(
                row["strip_query_prefixes"],
                field_path="strip_query_prefixes",
                strict=False,
            ),
            "strip_www": bool(row["strip_www"]),
            "force_https": bool(row["force_https"]),
            "enabled": bool(row["enabled"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    @staticmethod
    def _module_row_to_dict(row: asyncpg.Record) -> dict[str, Any]:
        return {
            "id": row["id"],
            "module_id": row["module_id"],
            "name": row["name"],
            "kind": row["kind"],
            "enabled": bool(row["enabled"]),
            "scopes": list(row["scopes"] or []),
            "trust_level": row["trust_level"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def _admin_job_row_to_dict(self, row: asyncpg.Record) -> dict[str, Any]:
        return {
            "id": row["id"],
            "kind": row["kind"],
            "target_type": row["target_type"],
            "target_id": row["target_id"],
            "status": row["status"],
            "attempt": int(row["attempt"]),
            "locked_by_module_id": row["locked_by_module_id"],
            "lease_expires_at": row["lease_expires_at"],
            "next_run_at": row["next_run_at"],
            "inputs_json": self._coerce_json_dict(row["inputs_json"]),
            "result_json": self._coerce_json_dict(row["result_json"]),
            "error_json": self._coerce_json_dict(row["error_json"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    async def get_posting(self, posting_id: str) -> dict[str, Any]:
        pool = await self._get_pool()
        try:
            row = await self._fetch_posting_detail_row(conn=pool, posting_id=posting_id)
        except (pg_exc.InvalidTextRepresentationError, asyncpg.DataError) as exc:
            raise RepositoryNotFoundError("posting not found") from exc
        if not row:
            raise RepositoryNotFoundError("posting not found")
        return self._posting_detail_row_to_dict(row)

    async def update_posting_status(
        self,
        *,
        posting_id: str,
        status: str,
        actor_user_id: str,
        reason: str | None,
    ) -> dict[str, Any]:
        pool = await self._get_pool()

        try:
            async with pool.acquire() as conn:
                async with conn.transaction():
                    posting_row = await conn.fetchrow(
                        """
                        select
                          id::text as id,
                          candidate_id::text as candidate_id,
                          status::text as status
                        from postings
                        where id = $1::uuid
                        for update
                        """,
                        posting_id,
                    )
                    if not posting_row:
                        raise RepositoryNotFoundError("posting not found")

                    from_status = str(posting_row["status"])
                    if status != from_status:
                        self._validate_posting_status_transition(from_status=from_status, to_status=status)

                    candidate_id = posting_row["candidate_id"]
                    from_candidate_state: str | None = None
                    to_candidate_state: str | None = None
                    if candidate_id:
                        candidate_row = await conn.fetchrow(
                            """
                            select state::text as state
                            from posting_candidates
                            where id = $1::uuid
                            for update
                            """,
                            candidate_id,
                        )
                        if candidate_row:
                            from_candidate_state = str(candidate_row["state"])
                            derived_candidate_state = self._derive_candidate_state_for_posting_status(status=status)
                            if derived_candidate_state and derived_candidate_state != from_candidate_state:
                                self._validate_candidate_transition(
                                    from_state=from_candidate_state,
                                    to_state=derived_candidate_state,
                                )
                                await conn.execute(
                                    """
                                    update posting_candidates
                                    set state = $2::candidate_state
                                    where id = $1::uuid
                                    """,
                                    candidate_id,
                                    derived_candidate_state,
                                )
                                to_candidate_state = derived_candidate_state

                    await conn.execute(
                        """
                        update postings
                        set
                          status = $2::posting_status,
                          published_at = case
                            when $2::posting_status = 'active' then coalesce(published_at, now())
                            else published_at
                          end
                        where id = $1::uuid
                        """,
                        posting_id,
                        status,
                    )

                    updated_row = await self._fetch_posting_detail_row(conn=conn, posting_id=posting_id)
                    if not updated_row:
                        raise RepositoryNotFoundError("posting not found")

                    await conn.execute(
                        """
                        insert into provenance_events (
                          entity_type,
                          entity_id,
                          event_type,
                          actor_type,
                          actor_id,
                          payload
                        )
                        values ('posting', $1::uuid, 'status_changed', 'human', $2::uuid, $3::jsonb)
                        """,
                        posting_id,
                        actor_user_id,
                        json.dumps(
                            {
                                "from_status": from_status,
                                "to_status": status,
                                "reason": reason,
                            }
                        ),
                    )

                    if candidate_id and to_candidate_state and from_candidate_state:
                        await conn.execute(
                            """
                            insert into provenance_events (
                              entity_type,
                              entity_id,
                              event_type,
                              actor_type,
                              actor_id,
                              payload
                            )
                            values ('posting_candidate', $1::uuid, 'state_changed', 'human', $2::uuid, $3::jsonb)
                            """,
                            candidate_id,
                            actor_user_id,
                            json.dumps(
                                {
                                    "from_state": from_candidate_state,
                                    "to_state": to_candidate_state,
                                    "reason": reason,
                                    "source": "posting_status_patch",
                                    "posting_id": posting_id,
                                }
                            ),
                        )

                    return self._posting_detail_row_to_dict(updated_row)
        except (pg_exc.InvalidTextRepresentationError, asyncpg.DataError) as exc:
            raise RepositoryNotFoundError("posting not found") from exc

    async def _apply_freshness_job_result(
        self,
        *,
        conn: asyncpg.Connection,
        job_id: str,
        posting_id: str,
        actor_module_db_id: str,
        result_json: dict[str, Any] | None,
    ) -> None:
        payload = result_json if isinstance(result_json, dict) else {}
        recommended_status = self._coerce_text(payload.get("recommended_status"))
        reason = self._coerce_text(payload.get("reason")) or "freshness_check"

        applied = False
        if recommended_status in {"active", "stale", "archived", "closed"}:
            applied = await self._apply_machine_posting_status_transition(
                conn=conn,
                posting_id=posting_id,
                to_status=recommended_status,
                actor_module_db_id=actor_module_db_id,
                reason=reason,
                source="check_freshness_job",
                job_id=job_id,
            )

        await conn.execute(
            """
            insert into provenance_events (
              entity_type,
              entity_id,
              event_type,
              actor_type,
              actor_id,
              payload
            )
            values ('job', $1::uuid, 'freshness_result_applied', 'machine', $2::uuid, $3::jsonb)
            """,
            job_id,
            actor_module_db_id,
            json.dumps(
                {
                    "posting_id": posting_id,
                    "recommended_status": recommended_status,
                    "reason": reason,
                    "applied": applied,
                }
            ),
        )

    async def _apply_freshness_dead_letter_fallback(
        self,
        *,
        conn: asyncpg.Connection,
        job_id: str,
        posting_id: str,
        actor_module_db_id: str,
        attempt: int,
    ) -> None:
        posting_row = await conn.fetchrow(
            """
            select status::text as status
            from postings
            where id = $1::uuid
            for update
            """,
            posting_id,
        )
        if not posting_row:
            return

        from_status = str(posting_row["status"])
        target_status: str | None = None
        if from_status == "active":
            target_status = "stale"
        elif from_status == "stale":
            target_status = "archived"

        applied = False
        if target_status:
            applied = await self._apply_machine_posting_status_transition(
                conn=conn,
                posting_id=posting_id,
                to_status=target_status,
                actor_module_db_id=actor_module_db_id,
                reason="freshness_retry_exhausted",
                source="check_freshness_retry_exhausted",
                job_id=job_id,
            )

        await conn.execute(
            """
            insert into provenance_events (
              entity_type,
              entity_id,
              event_type,
              actor_type,
              actor_id,
              payload
            )
            values ('job', $1::uuid, 'freshness_retry_exhausted', 'machine', $2::uuid, $3::jsonb)
            """,
            job_id,
            actor_module_db_id,
            json.dumps(
                {
                    "posting_id": posting_id,
                    "from_status": from_status,
                    "to_status": target_status,
                    "attempt": attempt,
                    "max_attempts": self.job_max_attempts,
                    "applied": applied,
                }
            ),
        )

    async def _apply_machine_posting_status_transition(
        self,
        *,
        conn: asyncpg.Connection,
        posting_id: str,
        to_status: str,
        actor_module_db_id: str,
        reason: str,
        source: str,
        job_id: str,
    ) -> bool:
        posting_row = await conn.fetchrow(
            """
            select
              id::text as id,
              candidate_id::text as candidate_id,
              status::text as status
            from postings
            where id = $1::uuid
            for update
            """,
            posting_id,
        )
        if not posting_row:
            return False

        from_status = str(posting_row["status"])
        if to_status == from_status:
            return False
        try:
            self._validate_posting_status_transition(from_status=from_status, to_status=to_status)
        except RepositoryConflictError:
            return False

        candidate_id = posting_row["candidate_id"]
        from_candidate_state: str | None = None
        to_candidate_state: str | None = None

        if candidate_id:
            candidate_row = await conn.fetchrow(
                """
                select state::text as state
                from posting_candidates
                where id = $1::uuid
                for update
                """,
                candidate_id,
            )
            if candidate_row:
                from_candidate_state = str(candidate_row["state"])
                derived_candidate_state = self._derive_candidate_state_for_posting_status(status=to_status)
                if derived_candidate_state and derived_candidate_state != from_candidate_state:
                    try:
                        self._validate_candidate_transition(
                            from_state=from_candidate_state,
                            to_state=derived_candidate_state,
                        )
                    except RepositoryConflictError:
                        return False
                    await conn.execute(
                        """
                        update posting_candidates
                        set state = $2::candidate_state
                        where id = $1::uuid
                        """,
                        candidate_id,
                        derived_candidate_state,
                    )
                    to_candidate_state = derived_candidate_state

        await conn.execute(
            """
            update postings
            set
              status = $2::posting_status,
              published_at = case
                when $2::posting_status = 'active' then coalesce(published_at, now())
                else published_at
              end
            where id = $1::uuid
            """,
            posting_id,
            to_status,
        )

        await conn.execute(
            """
            insert into provenance_events (
              entity_type,
              entity_id,
              event_type,
              actor_type,
              actor_id,
              payload
            )
            values ('posting', $1::uuid, 'status_changed', 'machine', $2::uuid, $3::jsonb)
            """,
            posting_id,
            actor_module_db_id,
            json.dumps(
                {
                    "from_status": from_status,
                    "to_status": to_status,
                    "reason": reason,
                    "source": source,
                    "job_id": job_id,
                }
            ),
        )

        if candidate_id and to_candidate_state and from_candidate_state:
            await conn.execute(
                """
                insert into provenance_events (
                  entity_type,
                  entity_id,
                  event_type,
                  actor_type,
                  actor_id,
                  payload
                )
                values ('posting_candidate', $1::uuid, 'state_changed', 'machine', $2::uuid, $3::jsonb)
                """,
                candidate_id,
                actor_module_db_id,
                json.dumps(
                    {
                        "from_state": from_candidate_state,
                        "to_state": to_candidate_state,
                        "reason": reason,
                        "source": source,
                        "posting_id": posting_id,
                        "job_id": job_id,
                    }
                ),
            )

        return True

    async def _fetch_candidate_row(self, *, conn: asyncpg.Connection, candidate_id: str) -> asyncpg.Record | None:
        return await conn.fetchrow(
            """
            select
              pc.id::text as id,
              pc.state::text as state,
              pc.dedupe_confidence,
              pc.risk_flags,
              pc.extracted_fields,
              coalesce(
                array_agg(distinct cd.discovery_id::text) filter (where cd.discovery_id is not null),
                '{}'
              ) as discovery_ids,
              p.id::text as posting_id,
              pc.created_at,
              pc.updated_at
            from posting_candidates pc
            left join candidate_discoveries cd on cd.candidate_id = pc.id
            left join postings p on p.candidate_id = pc.id
            where pc.id = $1::uuid
            group by pc.id, p.id
            """,
            candidate_id,
        )

    async def _fetch_posting_detail_row(
        self,
        *,
        conn: asyncpg.Connection | asyncpg.Pool,
        posting_id: str,
    ) -> asyncpg.Record | None:
        return await conn.fetchrow(
            """
            select
              id::text as id,
              candidate_id::text as candidate_id,
              title,
              canonical_url,
              normalized_url,
              canonical_hash,
              organization_name,
              sector,
              degree_level,
              opportunity_kind,
              country,
              region,
              city,
              remote,
              tags,
              areas,
              description_text,
              application_url,
              deadline,
              source_refs,
              status::text as status,
              published_at,
              updated_at,
              created_at
            from postings
            where id = $1::uuid
            """,
            posting_id,
        )

    async def _get_pool(self) -> asyncpg.Pool:
        if not self.database_url:
            raise RepositoryUnavailableError("SJ_DATABASE_URL is required")

        if self._pool is not None:
            return self._pool

        try:
            self._pool = await asyncpg.create_pool(
                dsn=self.database_url,
                min_size=self.min_pool_size,
                max_size=self.max_pool_size,
                command_timeout=15,
            )
            return self._pool
        except Exception as exc:  # pragma: no cover - depends on environment
            raise RepositoryUnavailableError("database unavailable") from exc

    @staticmethod
    def _job_row_to_dict(row: asyncpg.Record) -> dict[str, Any]:
        inputs_json = row["inputs_json"]
        if isinstance(inputs_json, str):
            try:
                inputs_json = json.loads(inputs_json)
            except json.JSONDecodeError:
                inputs_json = {}
        if inputs_json is None:
            inputs_json = {}

        return {
            "id": row["id"],
            "kind": row["kind"],
            "target_type": row["target_type"],
            "target_id": row["target_id"],
            "inputs_json": inputs_json,
            "status": row["status"],
        }

    @staticmethod
    def _candidate_row_to_dict(row: asyncpg.Record) -> dict[str, Any]:
        extracted_fields = row["extracted_fields"]
        if isinstance(extracted_fields, str):
            try:
                extracted_fields = json.loads(extracted_fields)
            except json.JSONDecodeError:
                extracted_fields = {}
        if not isinstance(extracted_fields, dict):
            extracted_fields = {}
        return {
            "id": row["id"],
            "state": row["state"],
            "dedupe_confidence": float(row["dedupe_confidence"]) if row["dedupe_confidence"] is not None else None,
            "risk_flags": list(row["risk_flags"] or []),
            "extracted_fields": extracted_fields,
            "discovery_ids": list(row["discovery_ids"] or []),
            "posting_id": row["posting_id"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    @staticmethod
    def _candidate_event_row_to_dict(row: asyncpg.Record) -> dict[str, Any]:
        payload = row["payload"]
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                payload = {}
        if not isinstance(payload, dict):
            payload = {}
        return {
            "id": int(row["id"]),
            "entity_type": row["entity_type"],
            "entity_id": row["entity_id"],
            "event_type": row["event_type"],
            "actor_type": row["actor_type"],
            "actor_id": row["actor_id"],
            "payload": payload,
            "created_at": row["created_at"],
        }

    @staticmethod
    def _posting_list_row_to_dict(row: asyncpg.Record) -> dict[str, Any]:
        return {
            "id": row["id"],
            "title": row["title"],
            "organization_name": row["organization_name"],
            "canonical_url": row["canonical_url"],
            "status": row["status"],
            "country": row["country"],
            "remote": bool(row["remote"]),
            "tags": list(row["tags"] or []),
            "updated_at": row["updated_at"],
            "created_at": row["created_at"],
        }

    @staticmethod
    def _posting_detail_row_to_dict(row: asyncpg.Record) -> dict[str, Any]:
        source_refs = row["source_refs"]
        if isinstance(source_refs, str):
            try:
                source_refs = json.loads(source_refs)
            except json.JSONDecodeError:
                source_refs = []
        if not isinstance(source_refs, list):
            source_refs = []
        source_refs = [item for item in source_refs if isinstance(item, dict)]

        return {
            "id": row["id"],
            "candidate_id": row["candidate_id"],
            "title": row["title"],
            "canonical_url": row["canonical_url"],
            "normalized_url": row["normalized_url"],
            "canonical_hash": row["canonical_hash"],
            "organization_name": row["organization_name"],
            "sector": row["sector"],
            "degree_level": row["degree_level"],
            "opportunity_kind": row["opportunity_kind"],
            "country": row["country"],
            "region": row["region"],
            "city": row["city"],
            "remote": bool(row["remote"]),
            "tags": list(row["tags"] or []),
            "areas": list(row["areas"] or []),
            "description_text": row["description_text"],
            "application_url": row["application_url"],
            "deadline": row["deadline"],
            "source_refs": source_refs,
            "status": row["status"],
            "published_at": row["published_at"],
            "updated_at": row["updated_at"],
            "created_at": row["created_at"],
        }

    @staticmethod
    def _resolve_postings_sort_expr(sort_by: str) -> str:
        sort_map = {
            "created_at": "p.created_at",
            "updated_at": "p.updated_at",
            "deadline": "p.deadline",
            "published_at": "p.published_at",
        }
        return sort_map.get(sort_by, "p.created_at")

    @staticmethod
    def _validate_candidate_transition(*, from_state: str, to_state: str) -> None:
        allowed_transitions = {
            "discovered": {"processed", "needs_review", "rejected", "archived"},
            "processed": {"publishable", "needs_review", "rejected", "archived"},
            "needs_review": {"publishable", "rejected", "archived", "processed"},
            "publishable": {"published", "rejected", "needs_review", "archived"},
            "published": {"archived", "closed"},
            "archived": {"published", "closed"},
            "closed": {"archived"},
            "rejected": {"needs_review", "archived"},
        }
        if to_state == from_state:
            return
        allowed = allowed_transitions.get(from_state)
        if not allowed or to_state not in allowed:
            raise RepositoryConflictError(f"invalid state transition: {from_state} -> {to_state}")

    @staticmethod
    def _validate_posting_status_transition(*, from_status: str, to_status: str) -> None:
        allowed_transitions = {
            "active": {"stale", "archived", "closed"},
            "stale": {"active", "archived", "closed"},
            "archived": {"active", "stale", "closed"},
            "closed": {"archived"},
        }
        if to_status == from_status:
            return
        allowed = allowed_transitions.get(from_status)
        if not allowed or to_status not in allowed:
            raise RepositoryConflictError(f"invalid posting status transition: {from_status} -> {to_status}")

    @staticmethod
    def _derive_candidate_state_for_posting_status(*, status: str) -> str | None:
        state_by_status = {
            "active": "published",
            "stale": "published",
            "archived": "archived",
            "closed": "closed",
        }
        return state_by_status.get(status)

    @staticmethod
    def _derive_posting_status_for_candidate_state(state: str) -> str | None:
        status_by_state = {
            "published": "active",
            "archived": "archived",
            "closed": "closed",
            "rejected": "archived",
        }
        return status_by_state.get(state)

    def _compute_retry_delay_seconds(self, *, attempt: int) -> int:
        if self.job_retry_base_seconds <= 0:
            return 0
        multiplier = max(0, attempt - 1)
        delay = self.job_retry_base_seconds * (2**multiplier)
        return min(delay, self.job_retry_max_seconds)

    @staticmethod
    def _coerce_text(value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return str(value)

    @staticmethod
    def _coerce_text_list(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        items: list[str] = []
        for item in value:
            if not isinstance(item, str):
                continue
            stripped = item.strip()
            if stripped:
                items.append(stripped)
        return items

    @staticmethod
    def _coerce_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _coerce_int(value: Any) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _coerce_bool(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on"}:
                return True
            if normalized in {"0", "false", "no", "off"}:
                return False
        return False

    @staticmethod
    def _coerce_datetime(value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            candidate = value.strip()
            if not candidate:
                return None
            try:
                return datetime.fromisoformat(candidate.replace("Z", "+00:00"))
            except ValueError:
                return None
        return None

    @staticmethod
    def _coerce_json_list(value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []
        items: list[dict[str, Any]] = []
        for item in value:
            if isinstance(item, dict):
                items.append(item)
        return items

    @staticmethod
    def _coerce_json_dict(value: Any) -> dict[str, Any]:
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                return {}
        if isinstance(value, dict):
            return value
        return {}

    def _normalize_url_override_domain(
        self,
        domain: Any,
        *,
        field_path: str,
        allow_none: bool = False,
    ) -> str | None:
        normalized = self._coerce_text(domain)
        if normalized is None:
            if allow_none:
                return None
            raise RepositoryValidationError(f"{field_path} must be a non-empty string")

        candidate = normalized.lower().lstrip(".")
        if not URL_OVERRIDE_DOMAIN_RE.match(candidate):
            raise RepositoryValidationError(f"{field_path} must be a valid lowercase domain")
        return candidate

    def _normalize_url_override_tokens(
        self,
        value: Any,
        *,
        field_path: str,
        strict: bool,
    ) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            if strict:
                raise RepositoryValidationError(f"{field_path} must be a list of lowercase strings")
            return []

        normalized: list[str] = []
        for index, item in enumerate(value):
            if not isinstance(item, str):
                if strict:
                    raise RepositoryValidationError(f"{field_path}[{index}] must be a lowercase string")
                continue
            token = item.strip().lower()
            if not token:
                if strict:
                    raise RepositoryValidationError(f"{field_path}[{index}] must be a lowercase string")
                continue
            if not URL_OVERRIDE_TOKEN_RE.match(token):
                if strict:
                    raise RepositoryValidationError(
                        f"{field_path}[{index}] must contain only lowercase letters, digits, ., _ or -",
                    )
                continue
            if token not in normalized:
                normalized.append(token)
        normalized.sort()
        return normalized

    def _build_url_normalization_override_rules(
        self,
        rows: list[asyncpg.Record],
    ) -> dict[str, dict[str, Any]]:
        rules: dict[str, dict[str, Any]] = {}
        for row in rows:
            domain = self._normalize_url_override_domain(row["domain"], field_path="domain", allow_none=True)
            if not domain:
                continue
            rules[domain] = {
                "strip_query_params": self._normalize_url_override_tokens(
                    row["strip_query_params"],
                    field_path="strip_query_params",
                    strict=False,
                ),
                "strip_query_prefixes": self._normalize_url_override_tokens(
                    row["strip_query_prefixes"],
                    field_path="strip_query_prefixes",
                    strict=False,
                ),
                "strip_www": bool(row["strip_www"]),
                "force_https": bool(row["force_https"]),
            }
        return rules

    async def _fetch_enabled_url_normalization_overrides_json(self, *, conn: asyncpg.Connection) -> str | None:
        rows = await conn.fetch(
            """
            select
              domain,
              strip_query_params,
              strip_query_prefixes,
              strip_www,
              force_https
            from url_normalization_overrides
            where enabled = true
            order by domain asc
            """,
        )
        rules = self._build_url_normalization_override_rules(rows)
        if not rules:
            return None
        return json.dumps(rules, separators=(",", ":"), sort_keys=True)

    def _validate_source_trust_policy_rules_json(self, rules_json: Any, *, strict: bool) -> dict[str, Any]:
        raw_rules = self._coerce_json_dict(rules_json)
        if strict and not isinstance(rules_json, dict):
            raise RepositoryValidationError("rules_json must be a JSON object")
        if not raw_rules:
            return {}

        unknown_top_level = sorted(set(raw_rules) - SOURCE_POLICY_RULE_KEYS)
        if unknown_top_level:
            if strict:
                unknown = ", ".join(unknown_top_level)
                raise RepositoryValidationError(f"rules_json contains unsupported keys: {unknown}")
            raw_rules = {key: value for key, value in raw_rules.items() if key in SOURCE_POLICY_RULE_KEYS}

        normalized_rules: dict[str, Any] = {}
        if "min_confidence" in raw_rules:
            min_confidence = self._coerce_float(raw_rules.get("min_confidence"))
            if min_confidence is None:
                if strict:
                    raise RepositoryValidationError("min_confidence must be a number")
            elif min_confidence < 0.0 or min_confidence > 1.0:
                if strict:
                    raise RepositoryValidationError("min_confidence must be between 0.0 and 1.0")
            else:
                normalized_rules["min_confidence"] = min_confidence

        return normalized_rules

    @staticmethod
    def _has_projection_signal(*, extraction: dict[str, Any], projection_payload: dict[str, Any]) -> bool:
        if "posting" in extraction and isinstance(extraction["posting"], dict):
            return True
        projection_keys = {
            "title",
            "organization_name",
            "canonical_url",
            "normalized_url",
            "canonical_hash",
            "tags",
            "areas",
            "country",
            "region",
            "city",
            "description_text",
            "application_url",
            "deadline",
            "source_refs",
        }
        return any(key in projection_payload for key in projection_keys)

    @staticmethod
    def _merge_risk_flags(*groups: list[str]) -> list[str]:
        merged: list[str] = []
        seen: set[str] = set()
        for group in groups:
            for value in group:
                normalized = value.strip()
                if not normalized:
                    continue
                key = normalized.casefold()
                if key in seen:
                    continue
                seen.add(key)
                merged.append(normalized)
        return merged

    async def _evaluate_dedupe_merge_policy(
        self,
        *,
        conn: asyncpg.Connection,
        extraction: dict[str, Any],
        projection_payload: dict[str, Any],
        canonical_hash: str | None,
        normalized_url: str | None,
        canonical_url: str | None,
        application_url: str | None,
        title: str | None,
        organization_name: str | None,
        description_text: str | None,
        tags: list[str],
        areas: list[str],
        country: str | None,
        region: str | None,
        city: str | None,
        can_project_posting: bool,
    ) -> DedupePolicyDecision:
        if not can_project_posting:
            return DedupePolicyDecision(
                decision="none",
                primary_candidate_id=None,
                confidence=None,
                risk_flags=[],
                metadata={"reason": "projection_unavailable"},
            )
        if not any([canonical_hash, normalized_url, canonical_url, application_url, organization_name]):
            return DedupePolicyDecision(
                decision="none",
                primary_candidate_id=None,
                confidence=None,
                risk_flags=[],
                metadata={"reason": "missing_dedupe_keys"},
            )

        rows = await conn.fetch(
            """
            select
              pc.id::text as candidate_id,
              pc.extracted_fields,
              p.id::text as posting_id,
              p.canonical_hash,
              p.normalized_url,
              p.canonical_url,
              p.application_url,
              p.title,
              p.organization_name,
              p.description_text,
              p.tags,
              p.areas,
              p.country,
              p.region,
              p.city
            from posting_candidates pc
            join postings p on p.candidate_id = pc.id
            where pc.state::text <> 'archived'
              and (
                ($1::text is not null and p.canonical_hash = $1)
                or ($2::text is not null and p.normalized_url = $2)
                or ($3::text is not null and p.canonical_url = $3)
                or ($4::text is not null and p.application_url = $4)
              )
            order by pc.updated_at desc, pc.id asc
            limit 25
            """,
            canonical_hash,
            normalized_url,
            canonical_url,
            application_url,
        )
        if not rows:
            return DedupePolicyDecision(
                decision="none",
                primary_candidate_id=None,
                confidence=None,
                risk_flags=[],
                metadata={"reason": "no_candidate_matches"},
            )

        incoming = DedupeCandidateSnapshot(
            candidate_id="incoming",
            canonical_hash=canonical_hash,
            normalized_url=normalized_url,
            canonical_url=canonical_url,
            application_url=application_url,
            title=title,
            organization_name=organization_name,
            description_text=description_text,
            tags=tags,
            areas=areas,
            country=country,
            region=region,
            city=city,
            named_entities=extract_named_entities(extraction),
            contact_domains=self._merge_risk_flags(
                extract_contact_domains(extraction),
                extract_contact_domains(projection_payload),
            ),
            has_posting=True,
        )

        existing: list[DedupeCandidateSnapshot] = []
        for row in rows:
            extracted_fields = self._coerce_json_dict(row["extracted_fields"])
            extracted_posting = self._coerce_json_dict(extracted_fields.get("posting"))
            existing.append(
                DedupeCandidateSnapshot(
                    candidate_id=row["candidate_id"],
                    canonical_hash=self._coerce_text(row["canonical_hash"]),
                    normalized_url=self._coerce_text(row["normalized_url"]),
                    canonical_url=self._coerce_text(row["canonical_url"]),
                    application_url=self._coerce_text(row["application_url"]),
                    title=self._coerce_text(row["title"]) or self._coerce_text(extracted_posting.get("title")),
                    organization_name=self._coerce_text(row["organization_name"])
                    or self._coerce_text(extracted_posting.get("organization_name")),
                    description_text=self._coerce_text(row["description_text"])
                    or self._coerce_text(extracted_posting.get("description_text")),
                    tags=list(row["tags"] or []),
                    areas=list(row["areas"] or []),
                    country=self._coerce_text(row["country"]),
                    region=self._coerce_text(row["region"]),
                    city=self._coerce_text(row["city"]),
                    named_entities=extract_named_entities(extracted_fields),
                    contact_domains=self._merge_risk_flags(
                        extract_contact_domains(extracted_fields),
                        extract_contact_domains(extracted_posting),
                    ),
                    has_posting=bool(row["posting_id"]),
                )
            )

        return evaluate_merge_policy(incoming=incoming, existing=existing)

    @staticmethod
    def _resolve_source_key_hint(
        *,
        extraction: dict[str, Any],
        projection_payload: dict[str, Any],
        discovery_metadata: dict[str, Any],
    ) -> str | None:
        for candidate in (
            projection_payload.get("source_key"),
            extraction.get("source_key"),
            discovery_metadata.get("source_key"),
        ):
            if isinstance(candidate, str):
                normalized = candidate.strip()
                if normalized:
                    return normalized
        return None

    async def _resolve_source_trust_policy(
        self,
        *,
        conn: asyncpg.Connection,
        source_key_hint: str | None,
        module_id: str,
        module_trust_level: str,
    ) -> SourceTrustPolicyRecord:
        normalized_trust_level = module_trust_level if module_trust_level in {"trusted", "semi_trusted", "untrusted"} else "untrusted"
        policy_lookup_order: list[str] = []
        if source_key_hint:
            policy_lookup_order.append(source_key_hint)
        if module_id:
            policy_lookup_order.append(f"module:{module_id}")
        policy_lookup_order.append(f"default:{normalized_trust_level}")

        row = await conn.fetchrow(
            """
            select
              source_key,
              trust_level::text as trust_level,
              auto_publish,
              requires_moderation,
              rules_json
            from source_trust_policy
            where enabled = true
              and source_key = any($1::text[])
            order by array_position($1::text[], source_key)
            limit 1
            """,
            policy_lookup_order,
        )
        if row:
            return SourceTrustPolicyRecord(
                source_key=row["source_key"],
                trust_level=row["trust_level"],
                auto_publish=bool(row["auto_publish"]),
                requires_moderation=bool(row["requires_moderation"]),
                rules_json=self._validate_source_trust_policy_rules_json(row["rules_json"], strict=False),
                matched_fallback=False,
            )

        default_auto_publish = normalized_trust_level in {"trusted", "semi_trusted"}
        default_requires_moderation = normalized_trust_level == "untrusted"
        default_rules_json: dict[str, Any] = {}

        return SourceTrustPolicyRecord(
            source_key=f"default:{normalized_trust_level}",
            trust_level=normalized_trust_level,
            auto_publish=default_auto_publish,
            requires_moderation=default_requires_moderation,
            rules_json=default_rules_json,
            matched_fallback=True,
        )

    def _resolve_publish_decision(
        self,
        *,
        can_project_posting: bool,
        trust_policy: SourceTrustPolicyRecord,
        dedupe_confidence: float | None,
        risk_flags: list[str],
    ) -> tuple[str, str, dict[str, Any]]:
        rules_json: dict[str, Any] = {}
        min_confidence: float | None = 0.72 if trust_policy.trust_level in {"trusted", "semi_trusted"} else None
        meets_confidence = min_confidence is None or (
            dedupe_confidence is not None and dedupe_confidence >= min_confidence
        )
        has_conflict_flag = any("conflict" in flag.lower() for flag in risk_flags)

        should_auto_publish = False
        reason = "insufficient_projection_data"

        if can_project_posting:
            trust_level = trust_policy.trust_level
            if trust_level == "trusted":
                should_auto_publish = (
                    trust_policy.auto_publish
                    and not trust_policy.requires_moderation
                    and meets_confidence
                )
                if should_auto_publish:
                    reason = "trusted_auto_publish"
                elif not trust_policy.auto_publish:
                    reason = "policy_auto_publish_disabled"
                elif trust_policy.requires_moderation:
                    reason = "policy_requires_moderation"
                elif not meets_confidence:
                    reason = "below_min_confidence"
            elif trust_level == "semi_trusted":
                should_auto_publish = (
                    trust_policy.auto_publish
                    and meets_confidence
                    and not has_conflict_flag
                    and not trust_policy.requires_moderation
                )
                if should_auto_publish:
                    reason = "semi_trusted_auto_publish"
                elif has_conflict_flag:
                    reason = "semi_trusted_conflict_flag"
                elif trust_policy.requires_moderation:
                    reason = "policy_requires_moderation"
                elif not meets_confidence:
                    reason = "below_min_confidence"
                elif not trust_policy.auto_publish:
                    reason = "policy_auto_publish_disabled"
            else:
                reason = "untrusted_requires_moderation"

        candidate_state = "processed"
        posting_status = "archived"
        if can_project_posting:
            candidate_state = "published" if should_auto_publish else "needs_review"
            posting_status = "active" if should_auto_publish else "archived"

        return (
            candidate_state,
            posting_status,
            {
                "source_key": trust_policy.source_key,
                "trust_level": trust_policy.trust_level,
                "auto_publish": trust_policy.auto_publish,
                "requires_moderation": trust_policy.requires_moderation,
                "rules_json": rules_json,
                "matched_fallback": trust_policy.matched_fallback,
                "dedupe_confidence": dedupe_confidence,
                "min_confidence": min_confidence,
                "meets_confidence": meets_confidence,
                "has_conflict_flag": has_conflict_flag,
                "reason": reason,
            },
        )

    def _resolve_merge_decision_routing(
        self,
        *,
        trust_policy: SourceTrustPolicyRecord,
        merge_decision: str,
        candidate_state: str,
        posting_status: str,
    ) -> tuple[str, str, str | None, str | None]:
        reason_defaults: dict[str, str] = {
            "needs_review": "dedupe_review_required",
            "auto_merged": "dedupe_auto_merged",
            "rejected": "dedupe_rejected",
        }
        action_defaults: dict[str, str] = {
            "needs_review": "needs_review",
            "auto_merged": "archive",
            "rejected": "reject",
        }

        reason = reason_defaults.get(merge_decision)
        action = action_defaults.get(merge_decision)

        if action == "needs_review":
            candidate_state = "needs_review"
            posting_status = "archived"
        elif action == "reject":
            candidate_state = "rejected"
            posting_status = "archived"
        elif action == "archive":
            candidate_state = "archived"
            posting_status = "archived"

        moderation_route: str | None = None
        return candidate_state, posting_status, reason, moderation_route

    @staticmethod
    def _coerce_candidate_state(value: Any, *, default: str) -> str:
        allowed = {
            "discovered",
            "processed",
            "publishable",
            "published",
            "rejected",
            "closed",
            "archived",
            "needs_review",
        }
        if isinstance(value, str) and value in allowed:
            return value
        return default

    @staticmethod
    def _coerce_posting_status(value: Any, *, default: str) -> str:
        allowed = {"active", "stale", "archived", "closed"}
        if isinstance(value, str) and value in allowed:
            return value
        return default


@lru_cache
def get_repository() -> PostgresRepository:
    settings = get_settings()
    return PostgresRepository(
        database_url=settings.database_url,
        min_pool_size=settings.database_pool_min_size,
        max_pool_size=settings.database_pool_max_size,
        job_max_attempts=settings.job_max_attempts,
        job_retry_base_seconds=settings.job_retry_base_seconds,
        job_retry_max_seconds=settings.job_retry_max_seconds,
        freshness_check_interval_hours=settings.freshness_check_interval_hours,
        freshness_stale_after_hours=settings.freshness_stale_after_hours,
        freshness_archive_after_hours=settings.freshness_archive_after_hours,
    )
