from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any

import asyncpg  # type: ignore[import-untyped]
from asyncpg import exceptions as pg_exc

from app.core.config import get_settings


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


@dataclass(slots=True)
class MachineCredentialRecord:
    module_db_id: str
    module_id: str
    scopes: list[str]
    key_hash: str


class PostgresRepository:
    def __init__(
        self,
        database_url: str | None,
        min_pool_size: int,
        max_pool_size: int,
        job_max_attempts: int,
        job_retry_base_seconds: int,
        job_retry_max_seconds: int,
    ) -> None:
        self.database_url = database_url
        self.min_pool_size = min_pool_size
        self.max_pool_size = max_pool_size
        self.job_max_attempts = max(1, job_max_attempts)
        self.job_retry_base_seconds = max(0, job_retry_base_seconds)
        self.job_retry_max_seconds = max(0, job_retry_max_seconds)
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
                    return self._job_row_to_dict(row)
        except (pg_exc.InvalidTextRepresentationError, asyncpg.DataError) as exc:
            raise RepositoryNotFoundError("job not found") from exc

    async def requeue_expired_claimed_jobs(self, module_db_id: str, limit: int) -> int:
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
                        values ('job', $1::uuid, 'lease_requeued', 'machine', $2::uuid, $3::jsonb)
                        """,
                        row["id"],
                        module_db_id,
                        json.dumps({"reason": "lease_expired"}),
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

                    if requested_status == "failed":
                        if attempt >= self.job_max_attempts:
                            resolved_status = "dead_letter"
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
                    elif requested_status == "failed" and resolved_status == "dead_letter":
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
                            values ('job', $1::uuid, 'dead_lettered', 'machine', $2::uuid, $3::jsonb)
                            """,
                            row["id"],
                            module_db_id,
                            json.dumps({"attempt": attempt, "max_attempts": self.job_max_attempts}),
                        )
                    return self._job_row_to_dict(row)
        except (pg_exc.InvalidTextRepresentationError, asyncpg.DataError) as exc:
            raise RepositoryNotFoundError("job not found") from exc

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
              id::text as id,
              url,
              normalized_url,
              canonical_hash,
              title_hint,
              metadata
            from discoveries
            where id = $1::uuid
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
        posting_status = self._coerce_posting_status(projection_payload.get("status"), default="active")

        can_project_posting = bool(
            has_projection_signal and title and organization_name and canonical_url and normalized_url and canonical_hash
        )
        default_state = "published" if can_project_posting else "processed"
        candidate_state = self._coerce_candidate_state(extraction.get("candidate_state"), default=default_state)
        if not can_project_posting and candidate_state == "published":
            candidate_state = "processed"

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
            self._coerce_float(extraction.get("dedupe_confidence")),
            json.dumps(extraction),
            self._coerce_text_list(extraction.get("risk_flags")),
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

        if not can_project_posting:
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
            self._coerce_text(projection_payload.get("country")),
            self._coerce_text(projection_payload.get("region")),
            self._coerce_text(projection_payload.get("city")),
            self._coerce_bool(projection_payload.get("remote")),
            self._coerce_text_list(projection_payload.get("tags")),
            self._coerce_text_list(projection_payload.get("areas")),
            self._coerce_text(projection_payload.get("description_text")),
            self._coerce_text(projection_payload.get("application_url")),
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

    async def list_candidates(self, limit: int, offset: int, state: str | None) -> list[dict[str, Any]]:
        pool = await self._get_pool()
        rows = await pool.fetch(
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
            where ($3::text is null or pc.state::text = $3::text)
            group by pc.id, p.id
            order by pc.updated_at desc
            limit $1
            offset $2
            """,
            limit,
            offset,
            state,
        )
        return [self._candidate_row_to_dict(row) for row in rows]

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
        if primary_candidate_id == secondary_candidate_id:
            raise RepositoryConflictError("primary and secondary candidate ids must differ")

        pool = await self._get_pool()
        try:
            async with pool.acquire() as conn:
                async with conn.transaction():
                    locked_rows = await conn.fetch(
                        """
                        select
                          id::text as id,
                          state::text as state
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
                    await conn.execute(
                        """
                        insert into candidate_merge_decisions (
                          primary_candidate_id,
                          secondary_candidate_id,
                          decision,
                          decided_by,
                          rationale,
                          metadata
                        )
                        values ($1::uuid, $2::uuid, 'manual_merged', $3, $4, $5::jsonb)
                        on conflict (primary_candidate_id, secondary_candidate_id)
                        do update set
                          decision = excluded.decision,
                          decided_by = excluded.decided_by,
                          rationale = excluded.rationale,
                          metadata = excluded.metadata
                        """,
                        primary_candidate_id,
                        secondary_candidate_id,
                        "human_moderator",
                        reason,
                        json.dumps({"actor_user_id": actor_user_id}),
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
                        values ('posting_candidate', $1::uuid, 'merge_applied', 'human', $2::uuid, $3::jsonb)
                        """,
                        primary_candidate_id,
                        actor_user_id,
                        json.dumps({"secondary_candidate_id": secondary_candidate_id, "reason": reason}),
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
                        values ('posting_candidate', $1::uuid, 'merged_away', 'human', $2::uuid, $3::jsonb)
                        """,
                        secondary_candidate_id,
                        actor_user_id,
                        json.dumps({"primary_candidate_id": primary_candidate_id, "reason": reason}),
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
                            values ('posting', $1::uuid, 'candidate_reassigned', 'human', $2::uuid, $3::jsonb)
                            """,
                            moved_posting_id,
                            actor_user_id,
                            json.dumps(
                                {
                                    "from_candidate_id": secondary_candidate_id,
                                    "to_candidate_id": primary_candidate_id,
                                    "reason": reason,
                                }
                            ),
                        )

                    row = await self._fetch_candidate_row(conn=conn, candidate_id=primary_candidate_id)
                    if not row:
                        raise RepositoryNotFoundError("candidate not found")
                    return self._candidate_row_to_dict(row)
        except (pg_exc.InvalidTextRepresentationError, asyncpg.DataError) as exc:
            raise RepositoryConflictError("invalid candidate id") from exc

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

        def bind(value: Any) -> str:
            params.append(value)
            return f"${len(params)}"

        if q:
            q_pattern = f"%{q.strip()}%"
            if q_pattern != "%%":
                token = bind(q_pattern)
                conditions.append(
                    f"(p.title ilike {token} or p.organization_name ilike {token} or coalesce(p.description_text, '') ilike {token})"
                )
        if organization_name:
            org_pattern = f"%{organization_name.strip()}%"
            if org_pattern != "%%":
                conditions.append(f"p.organization_name ilike {bind(org_pattern)}")
        if country:
            conditions.append(f"p.country ilike {bind(country.strip())}")
        if remote is not None:
            conditions.append(f"p.remote = {bind(remote)}")
        if status:
            conditions.append(f"p.status = {bind(status)}::posting_status")
        if tag:
            conditions.append(f"{bind(tag.strip())} = any(p.tags)")

        where_sql = " and ".join(conditions) if conditions else "true"
        sort_expr = self._resolve_postings_sort_expr(sort_by)
        direction = "asc" if sort_dir == "asc" else "desc"
        if sort_by in {"deadline", "published_at"}:
            order_by_sql = f"({sort_expr} is null) asc, {sort_expr} {direction}, p.id asc"
        else:
            order_by_sql = f"{sort_expr} {direction}, p.id asc"

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

    async def get_posting(self, posting_id: str) -> dict[str, Any]:
        pool = await self._get_pool()
        try:
            row = await pool.fetchrow(
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
        except (pg_exc.InvalidTextRepresentationError, asyncpg.DataError) as exc:
            raise RepositoryNotFoundError("posting not found") from exc
        if not row:
            raise RepositoryNotFoundError("posting not found")
        return self._posting_detail_row_to_dict(row)

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
    )
