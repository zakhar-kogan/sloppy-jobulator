from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
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
    def __init__(self, database_url: str | None, min_pool_size: int, max_pool_size: int) -> None:
        self.database_url = database_url
        self.min_pool_size = min_pool_size
        self.max_pool_size = max_pool_size
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
                    row = await conn.fetchrow(
                        """
                        update jobs
                        set
                          status = $3::job_status,
                          result_json = $4::jsonb,
                          error_json = $5::jsonb,
                          locked_by_module_id = null,
                          locked_at = null,
                          lease_expires_at = null
                        where id = $1::uuid
                          and status = 'claimed'
                          and locked_by_module_id = $2::uuid
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
                        status,
                        json.dumps(result_json) if result_json is not None else None,
                        json.dumps(error_json) if error_json is not None else None,
                    )

                    if not row:
                        existing = await conn.fetchrow(
                            "select id::text as id, status::text as status, locked_by_module_id::text as locked_by from jobs where id = $1::uuid",
                            job_id,
                        )
                        if not existing:
                            raise RepositoryNotFoundError("job not found")
                        if existing["locked_by"] != module_db_id:
                            raise RepositoryForbiddenError("job claimed by another module")
                        raise RepositoryConflictError("job is not in claimed state")

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
                        json.dumps({"status": status}),
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

    async def list_postings(self, limit: int, offset: int) -> list[dict[str, Any]]:
        pool = await self._get_pool()
        rows = await pool.fetch(
            """
            select
              id::text as id,
              title,
              organization_name,
              canonical_url,
              status::text as status,
              tags,
              created_at
            from postings
            order by created_at desc
            limit $1
            offset $2
            """,
            limit,
            offset,
        )
        return [
            {
                "id": row["id"],
                "title": row["title"],
                "organization_name": row["organization_name"],
                "canonical_url": row["canonical_url"],
                "status": row["status"],
                "tags": list(row["tags"] or []),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

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
    )
