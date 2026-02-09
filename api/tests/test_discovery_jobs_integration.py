from __future__ import annotations

import asyncio
import os
from collections.abc import Coroutine
from datetime import datetime, timezone
from typing import Any, TypeVar

import asyncpg  # type: ignore[import-untyped]
import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app
from app.services.repository import get_repository

CONNECTOR_HEADERS = {
    "X-Module-Id": "local-connector",
    "X-API-Key": "local-connector-key",
}

PROCESSOR_HEADERS = {
    "X-Module-Id": "local-processor",
    "X-API-Key": "local-processor-key",
}

T = TypeVar("T")


@pytest.fixture(scope="session")
def database_url() -> str:
    url = os.getenv("SJ_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not url:
        pytest.skip("integration tests require SJ_DATABASE_URL or DATABASE_URL")
    return url


@pytest.fixture(autouse=True)
def reset_tables(database_url: str) -> None:
    _run(_truncate_integration_tables(database_url))


@pytest.fixture
def api_client(database_url: str) -> TestClient:
    os.environ["SJ_DATABASE_URL"] = database_url
    get_settings.cache_clear()
    get_repository.cache_clear()

    with TestClient(app) as client:
        yield client

    get_repository.cache_clear()
    get_settings.cache_clear()


def test_discovery_enqueue_claim_result_and_projection_flow(api_client: TestClient, database_url: str) -> None:
    payload = {
        "origin_module_id": "local-connector",
        "external_id": "ext-123",
        "discovered_at": datetime.now(timezone.utc).isoformat(),
        "url": "https://example.edu/jobs/biostats-phd?utm_source=feed",
        "title_hint": "Biostatistics PhD Opportunity",
        "text_hint": "Funded position in translational medicine",
        "metadata": {"source": "integration-test"},
    }

    discovery_response = api_client.post("/discoveries", json=payload, headers=CONNECTOR_HEADERS)
    assert discovery_response.status_code == 202
    discovery_data = discovery_response.json()
    discovery_id = discovery_data["discovery_id"]
    assert discovery_id
    assert discovery_data["normalized_url"] is not None
    assert discovery_data["canonical_hash"] is not None

    jobs_response = api_client.get("/jobs", headers=PROCESSOR_HEADERS)
    assert jobs_response.status_code == 200
    jobs = jobs_response.json()
    assert len(jobs) == 1
    job_id = jobs[0]["id"]
    assert jobs[0]["status"] == "queued"
    assert jobs[0]["target_id"] == discovery_id

    claim_response = api_client.post(
        f"/jobs/{job_id}/claim",
        json={"lease_seconds": 120},
        headers=PROCESSOR_HEADERS,
    )
    assert claim_response.status_code == 200
    assert claim_response.json()["status"] == "claimed"

    projected_hash = discovery_data["canonical_hash"]
    result_response = api_client.post(
        f"/jobs/{job_id}/result",
        json={
            "status": "done",
            "result_json": {
                "dedupe_confidence": 0.992,
                "risk_flags": ["manual_review_low_confidence"],
                "posting": {
                    "title": "Biostatistics PhD Opportunity",
                    "organization_name": "Example University",
                    "canonical_url": "https://example.edu/jobs/biostats-phd",
                    "normalized_url": discovery_data["normalized_url"],
                    "canonical_hash": projected_hash,
                    "country": "US",
                    "remote": True,
                    "tags": ["biostatistics", "phd"],
                    "areas": ["medicine"],
                    "description_text": "Funded doctoral research program in translational medicine.",
                    "source_refs": [{"kind": "discovery", "id": discovery_id}],
                },
            },
        },
        headers=PROCESSOR_HEADERS,
    )
    assert result_response.status_code == 200
    assert result_response.json()["status"] == "done"

    done_job_count = _run(
        _fetchval(
            database_url,
            "select count(*) from jobs where id = $1::uuid and status = 'done'",
            job_id,
        )
    )
    assert done_job_count == 1

    candidate_count = _run(
        _fetchval(
            database_url,
            """
            select count(*)
            from posting_candidates pc
            join candidate_discoveries cd on cd.candidate_id = pc.id
            where cd.discovery_id = $1::uuid
              and pc.state = 'published'
            """,
            discovery_id,
        )
    )
    assert candidate_count == 1

    posting_count = _run(
        _fetchval(
            database_url,
            "select count(*) from postings where canonical_hash = $1",
            projected_hash,
        )
    )
    assert posting_count == 1

    job_event_count = _run(
        _fetchval(
            database_url,
            "select count(*) from provenance_events where entity_type = 'job' and entity_id = $1::uuid",
            job_id,
        )
    )
    assert job_event_count >= 2

    candidate_event_count = _run(
        _fetchval(
            database_url,
            """
            select count(*)
            from provenance_events
            where entity_type = 'posting_candidate'
              and event_type = 'materialized'
            """,
        )
    )
    assert candidate_event_count == 1

    posting_event_count = _run(
        _fetchval(
            database_url,
            """
            select count(*)
            from provenance_events
            where entity_type = 'posting'
              and event_type = 'projected'
            """,
        )
    )
    assert posting_event_count == 1


def test_discovery_idempotency_does_not_duplicate_job(api_client: TestClient) -> None:
    payload = {
        "origin_module_id": "local-connector",
        "external_id": "ext-idempotent-1",
        "discovered_at": datetime.now(timezone.utc).isoformat(),
        "url": "https://example.edu/jobs/chemistry-postdoc",
        "title_hint": "Postdoc in Chemistry",
        "text_hint": "Organic chemistry and catalysis",
        "metadata": {"source": "integration-test"},
    }

    first_response = api_client.post("/discoveries", json=payload, headers=CONNECTOR_HEADERS)
    assert first_response.status_code == 202
    first_discovery_id = first_response.json()["discovery_id"]

    second_response = api_client.post("/discoveries", json=payload, headers=CONNECTOR_HEADERS)
    assert second_response.status_code == 202
    second_discovery_id = second_response.json()["discovery_id"]

    assert second_discovery_id == first_discovery_id

    jobs_response = api_client.get("/jobs", headers=PROCESSOR_HEADERS)
    assert jobs_response.status_code == 200
    jobs = jobs_response.json()
    assert len(jobs) == 1
    assert jobs[0]["target_id"] == first_discovery_id


def test_postings_list_reads_from_database(api_client: TestClient, database_url: str) -> None:
    posting_id = _run(
        _fetchval(
            database_url,
            """
            insert into postings (
              title,
              canonical_url,
              normalized_url,
              canonical_hash,
              organization_name,
              tags
            )
            values ($1, $2, $3, $4, $5, $6::text[])
            returning id::text
            """,
            "Research Engineer, Platform Biology",
            "https://example.edu/jobs/research-engineer-platform-biology",
            "https://example.edu/jobs/research-engineer-platform-biology",
            "postings-hash-1",
            "Example Institute",
            ["ml", "biology"],
        )
    )
    assert posting_id

    response = api_client.get("/postings")
    assert response.status_code == 200
    postings = response.json()
    assert len(postings) == 1
    posting = postings[0]
    assert posting["id"] == posting_id
    assert posting["title"] == "Research Engineer, Platform Biology"
    assert posting["organization_name"] == "Example Institute"
    assert posting["status"] == "active"
    assert posting["tags"] == ["ml", "biology"]


def _run(coro: Coroutine[Any, Any, T]) -> T:
    return asyncio.run(coro)


async def _truncate_integration_tables(database_url: str) -> None:
    conn = await asyncpg.connect(database_url)
    try:
        await conn.execute(
            """
            truncate table
              candidate_evidence,
              candidate_discoveries,
              postings,
              posting_candidates,
              evidence,
              discoveries,
              jobs,
              provenance_events
            restart identity cascade
            """
        )
    finally:
        await conn.close()


async def _fetchval(database_url: str, query: str, *args: Any) -> Any:
    conn = await asyncpg.connect(database_url)
    try:
        return await conn.fetchval(query, *args)
    finally:
        await conn.close()
