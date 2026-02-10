from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Coroutine
from datetime import datetime, timezone
from typing import Any, TypeVar

import asyncpg  # type: ignore[import-untyped]
import pytest
from fastapi.testclient import TestClient

import app.core.security as security
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

LOCAL_CONNECTOR_KEY_HASH = "a061dd1a62bc85bc23d5625af753a75aec0d8f9e8e0ab21d4161ce1c6bd6a6d0"

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


def test_expired_claimed_jobs_are_requeued(api_client: TestClient, database_url: str) -> None:
    discovery_response = api_client.post(
        "/discoveries",
        json={
            "origin_module_id": "local-connector",
            "external_id": "ext-expired-lease",
            "discovered_at": datetime.now(timezone.utc).isoformat(),
            "url": "https://example.edu/jobs/expired-lease",
            "title_hint": "Lease Expiry Test Posting",
            "text_hint": "Lease expiry handling",
            "metadata": {"source": "integration-test"},
        },
        headers=CONNECTOR_HEADERS,
    )
    assert discovery_response.status_code == 202

    jobs_response = api_client.get("/jobs", headers=PROCESSOR_HEADERS)
    assert jobs_response.status_code == 200
    jobs = jobs_response.json()
    assert len(jobs) == 1
    job_id = jobs[0]["id"]

    claim_response = api_client.post(
        f"/jobs/{job_id}/claim",
        json={"lease_seconds": 120},
        headers=PROCESSOR_HEADERS,
    )
    assert claim_response.status_code == 200

    _run(
        _execute(
            database_url,
            "update jobs set lease_expires_at = now() - interval '5 minutes' where id = $1::uuid",
            job_id,
        )
    )

    reap_response = api_client.post(
        "/jobs/reap-expired",
        params={"limit": 10},
        headers=PROCESSOR_HEADERS,
    )
    assert reap_response.status_code == 200
    assert reap_response.json()["requeued"] == 1

    queued_count = _run(
        _fetchval(
            database_url,
            """
            select count(*)
            from jobs
            where id = $1::uuid
              and status = 'queued'
              and locked_by_module_id is null
              and lease_expires_at is null
            """,
            job_id,
        )
    )
    assert queued_count == 1

    lease_requeue_event_count = _run(
        _fetchval(
            database_url,
            """
            select count(*)
            from provenance_events
            where entity_type = 'job'
              and entity_id = $1::uuid
              and event_type = 'lease_requeued'
            """,
            job_id,
        )
    )
    assert lease_requeue_event_count == 1

    reclaim_response = api_client.post(
        f"/jobs/{job_id}/claim",
        json={"lease_seconds": 120},
        headers=PROCESSOR_HEADERS,
    )
    assert reclaim_response.status_code == 200
    assert reclaim_response.json()["status"] == "claimed"


def test_failed_results_retry_then_dead_letter(api_client: TestClient, database_url: str) -> None:
    discovery_response = api_client.post(
        "/discoveries",
        json={
            "origin_module_id": "local-connector",
            "external_id": "ext-retry-policy",
            "discovered_at": datetime.now(timezone.utc).isoformat(),
            "url": "https://example.edu/jobs/retry-policy",
            "title_hint": "Retry Policy Posting",
            "text_hint": "Retry and dead letter handling",
            "metadata": {"source": "integration-test"},
        },
        headers=CONNECTOR_HEADERS,
    )
    assert discovery_response.status_code == 202

    jobs_response = api_client.get("/jobs", headers=PROCESSOR_HEADERS)
    assert jobs_response.status_code == 200
    jobs = jobs_response.json()
    assert len(jobs) == 1
    job_id = jobs[0]["id"]

    expected_statuses = ["queued", "queued", "dead_letter"]
    for attempt, expected_status in enumerate(expected_statuses, start=1):
        claim_response = api_client.post(
            f"/jobs/{job_id}/claim",
            json={"lease_seconds": 120},
            headers=PROCESSOR_HEADERS,
        )
        assert claim_response.status_code == 200
        assert claim_response.json()["status"] == "claimed"

        result_response = api_client.post(
            f"/jobs/{job_id}/result",
            json={
                "status": "failed",
                "error_json": {"reason": "integration-failure", "attempt": attempt},
            },
            headers=PROCESSOR_HEADERS,
        )
        assert result_response.status_code == 200
        assert result_response.json()["status"] == expected_status

        if expected_status == "queued":
            _run(_execute(database_url, "update jobs set next_run_at = now() where id = $1::uuid", job_id))

    dead_letter_count = _run(
        _fetchval(
            database_url,
            "select count(*) from jobs where id = $1::uuid and status = 'dead_letter'",
            job_id,
        )
    )
    assert dead_letter_count == 1

    retry_event_count = _run(
        _fetchval(
            database_url,
            """
            select count(*)
            from provenance_events
            where entity_type = 'job'
              and entity_id = $1::uuid
              and event_type = 'retry_scheduled'
            """,
            job_id,
        )
    )
    assert retry_event_count == 2

    dead_letter_event_count = _run(
        _fetchval(
            database_url,
            """
            select count(*)
            from provenance_events
            where entity_type = 'job'
              and entity_id = $1::uuid
              and event_type = 'dead_lettered'
            """,
            job_id,
        )
    )
    assert dead_letter_event_count == 1


def test_enqueue_freshness_jobs_and_apply_machine_status_transitions(api_client: TestClient, database_url: str) -> None:
    active_candidate_id, active_posting_id = _run(
        _insert_candidate_and_posting(
            database_url,
            canonical_hash="freshness-active-hash",
            status="active",
            candidate_state="published",
        )
    )
    stale_candidate_id, stale_posting_id = _run(
        _insert_candidate_and_posting(
            database_url,
            canonical_hash="freshness-stale-hash",
            status="stale",
            candidate_state="published",
        )
    )

    enqueue_response = api_client.post(
        "/jobs/enqueue-freshness",
        params={"limit": 10},
        headers=PROCESSOR_HEADERS,
    )
    assert enqueue_response.status_code == 200
    assert enqueue_response.json()["enqueued"] == 2

    duplicate_enqueue_response = api_client.post(
        "/jobs/enqueue-freshness",
        params={"limit": 10},
        headers=PROCESSOR_HEADERS,
    )
    assert duplicate_enqueue_response.status_code == 200
    assert duplicate_enqueue_response.json()["enqueued"] == 0

    jobs_response = api_client.get("/jobs", headers=PROCESSOR_HEADERS)
    assert jobs_response.status_code == 200
    jobs = jobs_response.json()
    assert len(jobs) == 2
    assert {job["kind"] for job in jobs} == {"check_freshness"}

    for job in jobs:
        claim_response = api_client.post(
            f"/jobs/{job['id']}/claim",
            json={"lease_seconds": 120},
            headers=PROCESSOR_HEADERS,
        )
        assert claim_response.status_code == 200

        target_status = "stale" if job["target_id"] == active_posting_id else "archived"
        result_response = api_client.post(
            f"/jobs/{job['id']}/result",
            json={
                "status": "done",
                "result_json": {
                    "recommended_status": target_status,
                    "reason": "integration-freshness",
                },
            },
            headers=PROCESSOR_HEADERS,
        )
        assert result_response.status_code == 200
        assert result_response.json()["status"] == "done"

    active_status = _run(
        _fetchval(
            database_url,
            "select status::text from postings where id = $1::uuid",
            active_posting_id,
        )
    )
    assert active_status == "stale"

    stale_status = _run(
        _fetchval(
            database_url,
            "select status::text from postings where id = $1::uuid",
            stale_posting_id,
        )
    )
    assert stale_status == "archived"

    active_candidate_state = _run(
        _fetchval(
            database_url,
            "select state::text from posting_candidates where id = $1::uuid",
            active_candidate_id,
        )
    )
    assert active_candidate_state == "published"

    stale_candidate_state = _run(
        _fetchval(
            database_url,
            "select state::text from posting_candidates where id = $1::uuid",
            stale_candidate_id,
        )
    )
    assert stale_candidate_state == "archived"

    machine_status_change_events = _run(
        _fetchval(
            database_url,
            """
            select count(*)
            from provenance_events
            where entity_type = 'posting'
              and event_type = 'status_changed'
              and actor_type = 'machine'
              and payload->>'source' = 'check_freshness_job'
            """,
        )
    )
    assert machine_status_change_events == 2


def test_freshness_dead_letter_downgrades_posting_after_retries(api_client: TestClient, database_url: str) -> None:
    candidate_id, posting_id = _run(
        _insert_candidate_and_posting(
            database_url,
            canonical_hash="freshness-dead-letter-hash",
            status="active",
            candidate_state="published",
        )
    )

    enqueue_response = api_client.post(
        "/jobs/enqueue-freshness",
        params={"limit": 10},
        headers=PROCESSOR_HEADERS,
    )
    assert enqueue_response.status_code == 200
    assert enqueue_response.json()["enqueued"] == 1

    jobs_response = api_client.get("/jobs", headers=PROCESSOR_HEADERS)
    assert jobs_response.status_code == 200
    jobs = jobs_response.json()
    assert len(jobs) == 1
    job_id = jobs[0]["id"]
    assert jobs[0]["kind"] == "check_freshness"
    assert jobs[0]["target_id"] == posting_id

    expected_statuses = ["queued", "queued", "dead_letter"]
    for expected_status in expected_statuses:
        claim_response = api_client.post(
            f"/jobs/{job_id}/claim",
            json={"lease_seconds": 120},
            headers=PROCESSOR_HEADERS,
        )
        assert claim_response.status_code == 200
        assert claim_response.json()["status"] == "claimed"

        result_response = api_client.post(
            f"/jobs/{job_id}/result",
            json={
                "status": "failed",
                "error_json": {"reason": "freshness-check-timeout"},
            },
            headers=PROCESSOR_HEADERS,
        )
        assert result_response.status_code == 200
        assert result_response.json()["status"] == expected_status
        if expected_status == "queued":
            _run(_execute(database_url, "update jobs set next_run_at = now() where id = $1::uuid", job_id))

    posting_status = _run(
        _fetchval(
            database_url,
            "select status::text from postings where id = $1::uuid",
            posting_id,
        )
    )
    assert posting_status == "stale"

    candidate_state = _run(
        _fetchval(
            database_url,
            "select state::text from posting_candidates where id = $1::uuid",
            candidate_id,
        )
    )
    assert candidate_state == "published"

    retry_exhausted_events = _run(
        _fetchval(
            database_url,
            """
            select count(*)
            from provenance_events
            where entity_type = 'job'
              and entity_id = $1::uuid
              and event_type = 'freshness_retry_exhausted'
            """,
            job_id,
        )
    )
    assert retry_exhausted_events == 1

    machine_status_change_events = _run(
        _fetchval(
            database_url,
            """
            select count(*)
            from provenance_events
            where entity_type = 'posting'
              and entity_id = $1::uuid
              and event_type = 'status_changed'
              and actor_type = 'machine'
              and payload->>'source' = 'check_freshness_dead_letter'
            """,
            posting_id,
        )
    )
    assert machine_status_change_events == 1


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


def test_postings_filters_sort_pagination_and_detail(api_client: TestClient, database_url: str) -> None:
    _run(
        _execute(
            database_url,
            """
            insert into postings (
              title,
              canonical_url,
              normalized_url,
              canonical_hash,
              organization_name,
              country,
              remote,
              status,
              tags,
              description_text,
              created_at,
              updated_at
            )
            values
              ($1, $2, $2, $3, $4, 'US', true, 'active', $5::text[], 'biology platform role', now() - interval '3 days', now() - interval '3 days'),
              ($6, $7, $7, $8, $9, 'US', false, 'archived', $10::text[], 'chemistry role', now() - interval '2 days', now() - interval '2 days'),
              ($11, $12, $12, $13, $14, 'DE', true, 'active', $15::text[], 'ml engineer', now() - interval '1 day', now() - interval '1 day')
            """,
            "Research Engineer, Biology Platform",
            "https://example.edu/jobs/research-engineer-biology-platform",
            "g1-hash-1",
            "Example Institute",
            ["ml", "biology"],
            "Postdoc in Chemistry",
            "https://example.edu/jobs/postdoc-chemistry",
            "g1-hash-2",
            "Chem Lab",
            ["chemistry"],
            "Machine Learning Scientist",
            "https://example.edu/jobs/ml-scientist",
            "g1-hash-3",
            "Berlin AI Center",
            ["ml"],
        )
    )

    filtered_response = api_client.get(
        "/postings",
        params={"q": "biology", "country": "US", "remote": "true", "status": "active", "tag": "ml"},
    )
    assert filtered_response.status_code == 200
    filtered = filtered_response.json()
    assert len(filtered) == 1
    assert filtered[0]["title"] == "Research Engineer, Biology Platform"

    sorted_response = api_client.get("/postings", params={"sort_by": "updated_at", "sort_dir": "asc"})
    assert sorted_response.status_code == 200
    sorted_rows = sorted_response.json()
    assert len(sorted_rows) == 3
    assert sorted_rows[0]["title"] == "Research Engineer, Biology Platform"
    assert sorted_rows[2]["title"] == "Machine Learning Scientist"

    paged_response = api_client.get("/postings", params={"sort_by": "created_at", "sort_dir": "asc", "limit": 1, "offset": 1})
    assert paged_response.status_code == 200
    paged = paged_response.json()
    assert len(paged) == 1
    assert paged[0]["title"] == "Postdoc in Chemistry"

    detail_id = _run(
        _fetchval(
            database_url,
            "select id::text from postings where canonical_hash = 'g1-hash-1'",
        )
    )
    detail_response = api_client.get(f"/postings/{detail_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["id"] == detail_id
    assert detail["canonical_hash"] == "g1-hash-1"
    assert detail["country"] == "US"
    assert detail["remote"] is True
    assert detail["description_text"] == "biology platform role"


def test_postings_edge_query_semantics_and_deterministic_tie_breaks(
    api_client: TestClient,
    database_url: str,
) -> None:
    _run(
        _execute(
            database_url,
            """
            insert into postings (
              title,
              canonical_url,
              normalized_url,
              canonical_hash,
              organization_name,
              country,
              remote,
              status,
              tags,
              description_text,
              deadline,
              published_at,
              created_at,
              updated_at
            )
            values
              ($1, $2, $2, $3, $4, 'US', true, 'active', $5::text[], 'alpha role', now() + interval '2 days', now() - interval '5 days', now() - interval '10 days', now() - interval '1 day'),
              ($6, $7, $7, $8, $9, 'US', false, 'active', $10::text[], 'beta role', null, null, now() - interval '9 days', now() - interval '1 day'),
              ($11, $12, $12, $13, $14, 'CA', false, 'active', $15::text[], 'gamma role', now() + interval '1 day', now() - interval '6 days', now() - interval '8 days', now() - interval '3 days'),
              ($16, $17, $17, $18, $19, 'CA', false, 'active', $20::text[], 'delta role', null, null, now() - interval '7 days', now() - interval '3 days')
            """,
            "Alpha Position",
            "https://example.edu/jobs/alpha-position",
            "g1-edge-hash-1",
            "Alpha Org",
            ["Biology"],
            "Beta Position",
            "https://example.edu/jobs/beta-position",
            "g1-edge-hash-2",
            "Beta Org",
            ["chemistry"],
            "Gamma Position",
            "https://example.edu/jobs/gamma-position",
            "g1-edge-hash-3",
            "Gamma Org",
            ["ml"],
            "Delta Position",
            "https://example.edu/jobs/delta-position",
            "g1-edge-hash-4",
            "Delta Org",
            ["history"],
        )
    )

    whitespace_response = api_client.get(
        "/postings",
        params={
            "q": "   ",
            "organization_name": "   ",
            "country": "   ",
            "tag": "   ",
            "sort_by": "created_at",
            "sort_dir": "asc",
        },
    )
    assert whitespace_response.status_code == 200
    assert [row["title"] for row in whitespace_response.json()] == [
        "Alpha Position",
        "Beta Position",
        "Gamma Position",
        "Delta Position",
    ]

    trimmed_query_response = api_client.get("/postings", params={"q": "  alpha  "})
    assert trimmed_query_response.status_code == 200
    trimmed_rows = trimmed_query_response.json()
    assert len(trimmed_rows) == 1
    assert trimmed_rows[0]["title"] == "Alpha Position"

    tag_response = api_client.get("/postings", params={"tag": "biology"})
    assert tag_response.status_code == 200
    tag_rows = tag_response.json()
    assert len(tag_rows) == 1
    assert tag_rows[0]["title"] == "Alpha Position"

    country_response = api_client.get("/postings", params={"country": "us", "sort_by": "created_at", "sort_dir": "asc"})
    assert country_response.status_code == 200
    assert [row["title"] for row in country_response.json()] == ["Alpha Position", "Beta Position"]

    updated_asc_response = api_client.get("/postings", params={"sort_by": "updated_at", "sort_dir": "asc"})
    assert updated_asc_response.status_code == 200
    assert [row["title"] for row in updated_asc_response.json()] == [
        "Gamma Position",
        "Delta Position",
        "Alpha Position",
        "Beta Position",
    ]

    updated_desc_response = api_client.get("/postings", params={"sort_by": "updated_at", "sort_dir": "desc"})
    assert updated_desc_response.status_code == 200
    assert [row["title"] for row in updated_desc_response.json()] == [
        "Beta Position",
        "Alpha Position",
        "Delta Position",
        "Gamma Position",
    ]

    deadline_asc_response = api_client.get("/postings", params={"sort_by": "deadline", "sort_dir": "asc"})
    assert deadline_asc_response.status_code == 200
    assert [row["title"] for row in deadline_asc_response.json()] == [
        "Gamma Position",
        "Alpha Position",
        "Beta Position",
        "Delta Position",
    ]

    deadline_desc_response = api_client.get("/postings", params={"sort_by": "deadline", "sort_dir": "desc"})
    assert deadline_desc_response.status_code == 200
    assert [row["title"] for row in deadline_desc_response.json()] == [
        "Alpha Position",
        "Gamma Position",
        "Delta Position",
        "Beta Position",
    ]

    published_desc_response = api_client.get("/postings", params={"sort_by": "published_at", "sort_dir": "desc"})
    assert published_desc_response.status_code == 200
    assert [row["title"] for row in published_desc_response.json()] == [
        "Alpha Position",
        "Gamma Position",
        "Delta Position",
        "Beta Position",
    ]


def test_moderation_candidate_state_transitions_update_posting_status(
    api_client: TestClient,
    database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_mock_human_auth(monkeypatch, role="moderator", user_id="00000000-0000-0000-0000-000000000321")
    candidate_id, posting_id = _create_projected_candidate_and_posting(
        api_client,
        database_url,
        external_id="ext-mod-transition-1",
        canonical_hash="mod-transition-hash-1",
    )

    archive_response = api_client.patch(
        f"/candidates/{candidate_id}",
        json={"state": "archived", "reason": "position filled"},
        headers={"Authorization": "Bearer moderator-token"},
    )
    assert archive_response.status_code == 200
    assert archive_response.json()["state"] == "archived"

    archived_status_count = _run(
        _fetchval(
            database_url,
            "select count(*) from postings where id = $1::uuid and status = 'archived'",
            posting_id,
        )
    )
    assert archived_status_count == 1

    reopen_response = api_client.patch(
        f"/candidates/{candidate_id}",
        json={"state": "published", "reason": "reopened"},
        headers={"Authorization": "Bearer moderator-token"},
    )
    assert reopen_response.status_code == 200
    assert reopen_response.json()["state"] == "published"

    active_status_count = _run(
        _fetchval(
            database_url,
            """
            select count(*)
            from postings
            where id = $1::uuid
              and status = 'active'
              and published_at is not null
            """,
            posting_id,
        )
    )
    assert active_status_count == 1


def test_posting_lifecycle_patch_transitions_and_candidate_sync(
    api_client: TestClient,
    database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_mock_human_auth(monkeypatch, role="moderator", user_id="00000000-0000-0000-0000-000000000322")
    candidate_id, posting_id = _create_projected_candidate_and_posting(
        api_client,
        database_url,
        external_id="ext-posting-lifecycle-1",
        canonical_hash="posting-lifecycle-hash-1",
    )

    stale_response = api_client.patch(
        f"/postings/{posting_id}",
        json={"status": "stale", "reason": "freshness-check-warning"},
        headers={"Authorization": "Bearer moderator-token"},
    )
    assert stale_response.status_code == 200
    assert stale_response.json()["status"] == "stale"

    stale_candidate_state = _run(
        _fetchval(
            database_url,
            "select state::text from posting_candidates where id = $1::uuid",
            candidate_id,
        )
    )
    assert stale_candidate_state == "published"

    archived_response = api_client.patch(
        f"/postings/{posting_id}",
        json={"status": "archived", "reason": "stale-threshold-exceeded"},
        headers={"Authorization": "Bearer moderator-token"},
    )
    assert archived_response.status_code == 200
    assert archived_response.json()["status"] == "archived"

    archived_candidate_state = _run(
        _fetchval(
            database_url,
            "select state::text from posting_candidates where id = $1::uuid",
            candidate_id,
        )
    )
    assert archived_candidate_state == "archived"

    reopen_response = api_client.patch(
        f"/postings/{posting_id}",
        json={"status": "active", "reason": "source-confirmed-open"},
        headers={"Authorization": "Bearer moderator-token"},
    )
    assert reopen_response.status_code == 200
    assert reopen_response.json()["status"] == "active"
    assert reopen_response.json()["published_at"] is not None

    reopened_candidate_state = _run(
        _fetchval(
            database_url,
            "select state::text from posting_candidates where id = $1::uuid",
            candidate_id,
        )
    )
    assert reopened_candidate_state == "published"

    status_changed_event_count = _run(
        _fetchval(
            database_url,
            """
            select count(*)
            from provenance_events
            where entity_type = 'posting'
              and entity_id = $1::uuid
              and event_type = 'status_changed'
            """,
            posting_id,
        )
    )
    assert status_changed_event_count == 3


def test_posting_lifecycle_patch_rejects_invalid_transition(
    api_client: TestClient,
    database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_mock_human_auth(monkeypatch, role="moderator", user_id="00000000-0000-0000-0000-000000000323")
    _, posting_id = _create_projected_candidate_and_posting(
        api_client,
        database_url,
        external_id="ext-posting-lifecycle-2",
        canonical_hash="posting-lifecycle-hash-2",
    )

    close_response = api_client.patch(
        f"/postings/{posting_id}",
        json={"status": "closed", "reason": "position-closed"},
        headers={"Authorization": "Bearer moderator-token"},
    )
    assert close_response.status_code == 200
    assert close_response.json()["status"] == "closed"

    invalid_reopen_response = api_client.patch(
        f"/postings/{posting_id}",
        json={"status": "active", "reason": "invalid-direct-reopen"},
        headers={"Authorization": "Bearer moderator-token"},
    )
    assert invalid_reopen_response.status_code == 409

    status_after_conflict = _run(
        _fetchval(
            database_url,
            "select status::text from postings where id = $1::uuid",
            posting_id,
        )
    )
    assert status_after_conflict == "closed"


def test_moderation_invalid_transition_returns_conflict(
    api_client: TestClient,
    database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_mock_human_auth(monkeypatch, role="moderator", user_id="00000000-0000-0000-0000-000000000654")
    candidate_id, _ = _create_projected_candidate_and_posting(
        api_client,
        database_url,
        external_id="ext-mod-transition-2",
        canonical_hash="mod-transition-hash-2",
    )

    response = api_client.patch(
        f"/candidates/{candidate_id}",
        json={"state": "publishable", "reason": "invalid regression"},
        headers={"Authorization": "Bearer moderator-token"},
    )
    assert response.status_code == 409


def test_moderation_override_bypasses_transition_and_records_audit(
    api_client: TestClient,
    database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_mock_human_auth(monkeypatch, role="moderator", user_id="00000000-0000-0000-0000-000000000655")
    candidate_id, posting_id = _create_projected_candidate_and_posting(
        api_client,
        database_url,
        external_id="ext-mod-override-1",
        canonical_hash="mod-override-hash-1",
    )

    invalid_patch_response = api_client.patch(
        f"/candidates/{candidate_id}",
        json={"state": "publishable", "reason": "would be invalid without override"},
        headers={"Authorization": "Bearer moderator-token"},
    )
    assert invalid_patch_response.status_code == 409

    override_response = api_client.post(
        f"/candidates/{candidate_id}/override",
        json={"state": "publishable", "reason": "manual rollback", "posting_status": "archived"},
        headers={"Authorization": "Bearer moderator-token"},
    )
    assert override_response.status_code == 200
    assert override_response.json()["state"] == "publishable"

    posting_status_count = _run(
        _fetchval(
            database_url,
            """
            select count(*)
            from postings
            where id = $1::uuid
              and status = 'archived'
            """,
            posting_id,
        )
    )
    assert posting_status_count == 1

    events_response = api_client.get(
        f"/candidates/{candidate_id}/events",
        params={"limit": 20},
        headers={"Authorization": "Bearer moderator-token"},
    )
    assert events_response.status_code == 200
    event_types = [event["event_type"] for event in events_response.json()]
    assert "state_overridden" in event_types


def test_candidates_list_state_filter_with_human_auth(
    api_client: TestClient,
    database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_mock_human_auth(monkeypatch, role="moderator", user_id="00000000-0000-0000-0000-000000000777")
    candidate_id, _ = _create_projected_candidate_and_posting(
        api_client,
        database_url,
        external_id="ext-mod-list-1",
        canonical_hash="mod-list-hash-1",
    )

    _run(
        _execute(
            database_url,
            """
            insert into posting_candidates (state, extracted_fields)
            values ('needs_review', '{"title":"Needs review candidate"}'::jsonb)
            """,
        )
    )

    response = api_client.get(
        "/candidates",
        params={"state": "published", "limit": 10},
        headers={"Authorization": "Bearer moderator-token"},
    )
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["id"] == candidate_id


def test_moderation_merge_candidates_reassigns_posting_and_records_audit(
    api_client: TestClient,
    database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_mock_human_auth(monkeypatch, role="moderator", user_id="00000000-0000-0000-0000-000000000888")
    primary_candidate_id = _run(
        _fetchval(
            database_url,
            """
            insert into posting_candidates (state, extracted_fields)
            values ('needs_review', '{"title":"Primary candidate"}'::jsonb)
            returning id::text
            """,
        )
    )
    secondary_candidate_id, secondary_posting_id = _create_projected_candidate_and_posting(
        api_client,
        database_url,
        external_id="ext-merge-secondary",
        canonical_hash="merge-secondary-hash",
    )

    merge_response = api_client.post(
        f"/candidates/{primary_candidate_id}/merge",
        json={"secondary_candidate_id": secondary_candidate_id, "reason": "same opportunity duplicate"},
        headers={"Authorization": "Bearer moderator-token"},
    )
    assert merge_response.status_code == 200
    merged = merge_response.json()
    assert merged["id"] == primary_candidate_id

    reassigned_posting_count = _run(
        _fetchval(
            database_url,
            """
            select count(*)
            from postings
            where id = $1::uuid
              and candidate_id = $2::uuid
            """,
            secondary_posting_id,
            primary_candidate_id,
        )
    )
    assert reassigned_posting_count == 1

    secondary_archived_count = _run(
        _fetchval(
            database_url,
            """
            select count(*)
            from posting_candidates
            where id = $1::uuid
              and state = 'archived'
            """,
            secondary_candidate_id,
        )
    )
    assert secondary_archived_count == 1

    merge_decision_count = _run(
        _fetchval(
            database_url,
            """
            select count(*)
            from candidate_merge_decisions
            where primary_candidate_id = $1::uuid
              and secondary_candidate_id = $2::uuid
              and decision = 'manual_merged'
            """,
            primary_candidate_id,
            secondary_candidate_id,
        )
    )
    assert merge_decision_count == 1

    events_response = api_client.get(
        f"/candidates/{primary_candidate_id}/events",
        params={"limit": 20},
        headers={"Authorization": "Bearer moderator-token"},
    )
    assert events_response.status_code == 200
    event_types = [event["event_type"] for event in events_response.json()]
    assert "merge_applied" in event_types
    assert "candidate_reassigned" in event_types


def test_moderation_merge_conflict_when_both_candidates_have_postings(
    api_client: TestClient,
    database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_mock_human_auth(monkeypatch, role="moderator", user_id="00000000-0000-0000-0000-000000000999")
    primary_candidate_id, _ = _create_projected_candidate_and_posting(
        api_client,
        database_url,
        external_id="ext-merge-primary-conflict",
        canonical_hash="merge-primary-conflict-hash",
    )
    secondary_candidate_id, _ = _create_projected_candidate_and_posting(
        api_client,
        database_url,
        external_id="ext-merge-secondary-conflict",
        canonical_hash="merge-secondary-conflict-hash",
    )

    merge_response = api_client.post(
        f"/candidates/{primary_candidate_id}/merge",
        json={"secondary_candidate_id": secondary_candidate_id, "reason": "duplicate conflict"},
        headers={"Authorization": "Bearer moderator-token"},
    )
    assert merge_response.status_code == 409


def test_dedupe_policy_auto_merges_high_confidence_duplicate_candidate(
    api_client: TestClient,
    database_url: str,
) -> None:
    primary_candidate_id, primary_posting_id = _create_projected_candidate_and_posting(
        api_client,
        database_url,
        external_id="ext-dedupe-auto-primary",
        canonical_hash="dedupe-auto-merge-hash",
    )

    _create_projected_candidate_and_posting(
        api_client,
        database_url,
        external_id="ext-dedupe-auto-secondary",
        canonical_hash="dedupe-auto-merge-hash",
    )

    secondary_candidate_id = _run(
        _fetchval(
            database_url,
            """
            select secondary_candidate_id::text
            from candidate_merge_decisions
            where primary_candidate_id = $1::uuid
              and decision = 'auto_merged'
            order by created_at desc
            limit 1
            """,
            primary_candidate_id,
        )
    )
    assert secondary_candidate_id
    assert secondary_candidate_id != primary_candidate_id

    posting_candidate_id = _run(
        _fetchval(
            database_url,
            "select candidate_id::text from postings where id = $1::uuid",
            primary_posting_id,
        )
    )
    assert posting_candidate_id == primary_candidate_id

    discovery_link_count = _run(
        _fetchval(
            database_url,
            """
            select count(*)
            from candidate_discoveries
            where candidate_id = $1::uuid
            """,
            primary_candidate_id,
        )
    )
    assert discovery_link_count == 2

    secondary_state = _run(
        _fetchval(
            database_url,
            "select state::text from posting_candidates where id = $1::uuid",
            secondary_candidate_id,
        )
    )
    assert secondary_state == "archived"

    merge_confidence = _run(
        _fetchval(
            database_url,
            """
            select confidence
            from candidate_merge_decisions
            where primary_candidate_id = $1::uuid
              and secondary_candidate_id = $2::uuid
            """,
            primary_candidate_id,
            secondary_candidate_id,
        )
    )
    assert merge_confidence is not None
    assert float(merge_confidence) >= 0.93

    merge_actor_type = _run(
        _fetchval(
            database_url,
            """
            select actor_type
            from provenance_events
            where entity_type = 'posting_candidate'
              and entity_id = $1::uuid
              and event_type = 'merge_applied'
            order by id desc
            limit 1
            """,
            primary_candidate_id,
        )
    )
    assert merge_actor_type == "machine"


def test_dedupe_policy_routes_uncertain_match_to_review_queue(
    api_client: TestClient,
    database_url: str,
) -> None:
    primary_candidate_id, _ = _create_projected_candidate_and_posting(
        api_client,
        database_url,
        external_id="ext-dedupe-review-primary",
        canonical_hash="dedupe-review-primary-hash",
    )
    secondary_candidate_id, secondary_posting_id = _create_projected_candidate_and_posting(
        api_client,
        database_url,
        external_id="ext-dedupe-review-secondary",
        canonical_hash="dedupe-review-secondary-hash",
    )

    decision = _run(
        _fetchval(
            database_url,
            """
            select decision::text
            from candidate_merge_decisions
            where primary_candidate_id = $1::uuid
              and secondary_candidate_id = $2::uuid
            order by created_at desc
            limit 1
            """,
            primary_candidate_id,
            secondary_candidate_id,
        )
    )
    assert decision == "needs_review"

    secondary_state = _run(
        _fetchval(
            database_url,
            "select state::text from posting_candidates where id = $1::uuid",
            secondary_candidate_id,
        )
    )
    posting_status = _run(
        _fetchval(
            database_url,
            "select status::text from postings where id = $1::uuid",
            secondary_posting_id,
        )
    )
    risk_flags = _run(
        _fetchval(
            database_url,
            "select risk_flags from posting_candidates where id = $1::uuid",
            secondary_candidate_id,
        )
    )

    assert secondary_state == "needs_review"
    assert posting_status == "archived"
    assert "manual_review_low_signal" in list(risk_flags or [])


def test_trust_policy_blocks_publish_when_below_confidence_for_trusted_source(
    api_client: TestClient,
    database_url: str,
) -> None:
    candidate_id, posting_id = _create_projected_candidate_and_posting(
        api_client,
        database_url,
        external_id="ext-trust-confidence-low",
        canonical_hash="trust-confidence-low-hash",
        dedupe_confidence=0.40,
    )

    candidate_state = _run(
        _fetchval(
            database_url,
            "select state::text from posting_candidates where id = $1::uuid",
            candidate_id,
        )
    )
    posting_status = _run(
        _fetchval(
            database_url,
            "select status::text from postings where id = $1::uuid",
            posting_id,
        )
    )
    trust_policy_reason = _run(
        _fetchval(
            database_url,
            """
            select payload->>'reason'
            from provenance_events
            where entity_type = 'posting_candidate'
              and entity_id = $1::uuid
              and event_type = 'trust_policy_applied'
            order by id desc
            limit 1
            """,
            candidate_id,
        )
    )

    assert candidate_state == "needs_review"
    assert posting_status == "archived"
    assert trust_policy_reason == "below_min_confidence"


def test_trust_policy_allows_semi_trusted_without_conflict(
    api_client: TestClient,
    database_url: str,
) -> None:
    _run(_ensure_connector_module(database_url, module_id="semi-trusted-connector", trust_level="semi_trusted"))
    semi_trusted_headers = {
        "X-Module-Id": "semi-trusted-connector",
        "X-API-Key": "local-connector-key",
    }

    candidate_id, posting_id = _create_projected_candidate_and_posting(
        api_client,
        database_url,
        external_id="ext-semi-trusted-auto-publish",
        canonical_hash="semi-trusted-auto-publish-hash",
        connector_headers=semi_trusted_headers,
        dedupe_confidence=0.99,
    )

    candidate_state = _run(
        _fetchval(
            database_url,
            "select state::text from posting_candidates where id = $1::uuid",
            candidate_id,
        )
    )
    posting_status = _run(
        _fetchval(
            database_url,
            "select status::text from postings where id = $1::uuid",
            posting_id,
        )
    )

    assert candidate_state == "published"
    assert posting_status == "active"


def test_trust_policy_requires_moderation_for_untrusted_source(
    api_client: TestClient,
    database_url: str,
) -> None:
    _run(_ensure_connector_module(database_url, module_id="untrusted-connector", trust_level="untrusted"))
    untrusted_headers = {
        "X-Module-Id": "untrusted-connector",
        "X-API-Key": "local-connector-key",
    }

    candidate_id, posting_id = _create_projected_candidate_and_posting(
        api_client,
        database_url,
        external_id="ext-untrusted-review",
        canonical_hash="untrusted-review-hash",
        connector_headers=untrusted_headers,
        dedupe_confidence=1.0,
    )

    candidate_state = _run(
        _fetchval(
            database_url,
            "select state::text from posting_candidates where id = $1::uuid",
            candidate_id,
        )
    )
    posting_status = _run(
        _fetchval(
            database_url,
            "select status::text from postings where id = $1::uuid",
            posting_id,
        )
    )
    trust_policy_reason = _run(
        _fetchval(
            database_url,
            """
            select payload->>'reason'
            from provenance_events
            where entity_type = 'posting_candidate'
              and entity_id = $1::uuid
              and event_type = 'trust_policy_applied'
            order by id desc
            limit 1
            """,
            candidate_id,
        )
    )

    assert candidate_state == "needs_review"
    assert posting_status == "archived"
    assert trust_policy_reason == "untrusted_requires_moderation"


def test_trust_policy_uses_source_key_override(
    api_client: TestClient,
    database_url: str,
) -> None:
    _run(
        _upsert_source_trust_policy(
            database_url,
            source_key="tests:force-review",
            trust_level="trusted",
            auto_publish=False,
            requires_moderation=True,
            rules_json={"min_confidence": 0.0},
        )
    )

    candidate_id, posting_id = _create_projected_candidate_and_posting(
        api_client,
        database_url,
        external_id="ext-source-key-policy",
        canonical_hash="source-key-policy-hash",
        dedupe_confidence=0.99,
        source_key="tests:force-review",
    )

    candidate_state = _run(
        _fetchval(
            database_url,
            "select state::text from posting_candidates where id = $1::uuid",
            candidate_id,
        )
    )
    posting_status = _run(
        _fetchval(
            database_url,
            "select status::text from postings where id = $1::uuid",
            posting_id,
        )
    )
    applied_source_key = _run(
        _fetchval(
            database_url,
            """
            select payload->>'source_key'
            from provenance_events
            where entity_type = 'posting_candidate'
              and entity_id = $1::uuid
              and event_type = 'trust_policy_applied'
            order by id desc
            limit 1
            """,
            candidate_id,
        )
    )

    assert candidate_state == "needs_review"
    assert posting_status == "archived"
    assert applied_source_key == "tests:force-review"


def test_trust_policy_can_override_needs_review_merge_route_for_source(
    api_client: TestClient,
    database_url: str,
) -> None:
    _run(
        _upsert_source_trust_policy(
            database_url,
            source_key="tests:merge-needs-review",
            trust_level="trusted",
            auto_publish=True,
            requires_moderation=False,
            rules_json={
                "min_confidence": 0.0,
                "merge_decision_actions": {"needs_review": "reject"},
                "merge_decision_reasons": {"needs_review": "policy_merge_needs_review_reject"},
                "moderation_routes": {"needs_review": "dedupe.manual_triage"},
            },
        )
    )

    primary_candidate_id, _ = _create_projected_candidate_and_posting(
        api_client,
        database_url,
        external_id="ext-policy-needs-review-primary",
        canonical_hash="policy-needs-review-primary-hash",
    )
    secondary_candidate_id, secondary_posting_id = _create_projected_candidate_and_posting(
        api_client,
        database_url,
        external_id="ext-policy-needs-review-secondary",
        canonical_hash="policy-needs-review-secondary-hash",
        source_key="tests:merge-needs-review",
    )

    merge_decision = _run(
        _fetchval(
            database_url,
            """
            select decision::text
            from candidate_merge_decisions
            where primary_candidate_id = $1::uuid
              and secondary_candidate_id = $2::uuid
            order by created_at desc
            limit 1
            """,
            primary_candidate_id,
            secondary_candidate_id,
        )
    )
    secondary_state = _run(
        _fetchval(
            database_url,
            "select state::text from posting_candidates where id = $1::uuid",
            secondary_candidate_id,
        )
    )
    posting_status = _run(
        _fetchval(
            database_url,
            "select status::text from postings where id = $1::uuid",
            secondary_posting_id,
        )
    )
    trust_policy_reason = _run(
        _fetchval(
            database_url,
            """
            select payload->>'reason'
            from provenance_events
            where entity_type = 'posting_candidate'
              and entity_id = $1::uuid
              and event_type = 'trust_policy_applied'
            order by id desc
            limit 1
            """,
            secondary_candidate_id,
        )
    )
    moderation_route = _run(
        _fetchval(
            database_url,
            """
            select payload->>'moderation_route'
            from provenance_events
            where entity_type = 'posting_candidate'
              and entity_id = $1::uuid
              and event_type = 'trust_policy_applied'
            order by id desc
            limit 1
            """,
            secondary_candidate_id,
        )
    )

    assert merge_decision == "needs_review"
    assert secondary_state == "rejected"
    assert posting_status == "archived"
    assert trust_policy_reason == "policy_merge_needs_review_reject"
    assert moderation_route == "dedupe.manual_triage"


def test_trust_policy_can_override_rejected_merge_route_for_source(
    api_client: TestClient,
    database_url: str,
) -> None:
    _run(
        _upsert_source_trust_policy(
            database_url,
            source_key="tests:merge-rejected",
            trust_level="trusted",
            auto_publish=True,
            requires_moderation=False,
            rules_json={
                "min_confidence": 0.0,
                "merge_decision_actions": {"rejected": "needs_review"},
                "merge_decision_reasons": {"rejected": "policy_merge_rejected_review"},
                "moderation_routes": {"rejected": "dedupe.source_risk_review"},
            },
        )
    )

    primary_candidate_id, _ = _create_projected_candidate_and_posting(
        api_client,
        database_url,
        external_id="ext-policy-rejected-primary",
        canonical_hash="policy-rejected-primary-hash",
        title="Research Scientist Fellowship",
        organization_name="Example University Research Lab",
        tags=["science"],
        application_url="https://example.edu/apply/shared-form",
    )
    secondary_candidate_id, secondary_posting_id = _create_projected_candidate_and_posting(
        api_client,
        database_url,
        external_id="ext-policy-rejected-secondary",
        canonical_hash="policy-rejected-secondary-hash",
        source_key="tests:merge-rejected",
        title="Research Engineer Fellowship",
        organization_name="Example University Research Lab",
        tags=["engineering"],
        application_url="https://example.edu/apply/shared-form",
    )

    merge_decision = _run(
        _fetchval(
            database_url,
            """
            select decision::text
            from candidate_merge_decisions
            where primary_candidate_id = $1::uuid
              and secondary_candidate_id = $2::uuid
            order by created_at desc
            limit 1
            """,
            primary_candidate_id,
            secondary_candidate_id,
        )
    )
    secondary_state = _run(
        _fetchval(
            database_url,
            "select state::text from posting_candidates where id = $1::uuid",
            secondary_candidate_id,
        )
    )
    posting_status = _run(
        _fetchval(
            database_url,
            "select status::text from postings where id = $1::uuid",
            secondary_posting_id,
        )
    )
    trust_policy_reason = _run(
        _fetchval(
            database_url,
            """
            select payload->>'reason'
            from provenance_events
            where entity_type = 'posting_candidate'
              and entity_id = $1::uuid
              and event_type = 'trust_policy_applied'
            order by id desc
            limit 1
            """,
            secondary_candidate_id,
        )
    )
    moderation_route = _run(
        _fetchval(
            database_url,
            """
            select payload->>'moderation_route'
            from provenance_events
            where entity_type = 'posting_candidate'
              and entity_id = $1::uuid
              and event_type = 'trust_policy_applied'
            order by id desc
            limit 1
            """,
            secondary_candidate_id,
        )
    )

    assert merge_decision == "rejected"
    assert secondary_state == "needs_review"
    assert posting_status == "archived"
    assert trust_policy_reason == "policy_merge_rejected_review"
    assert moderation_route == "dedupe.source_risk_review"


def _configure_mock_human_auth(monkeypatch: pytest.MonkeyPatch, *, role: str, user_id: str) -> None:
    monkeypatch.setenv("SJ_SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SJ_SUPABASE_ANON_KEY", "anon-key")
    get_settings.cache_clear()

    async def _fake_fetch(**_: Any) -> dict[str, Any]:
        return {"id": user_id, "app_metadata": {"role": role}}

    monkeypatch.setattr(security, "_fetch_supabase_user", _fake_fetch)


def _create_projected_candidate_and_posting(
    api_client: TestClient,
    database_url: str,
    *,
    external_id: str,
    canonical_hash: str,
    connector_headers: dict[str, str] = CONNECTOR_HEADERS,
    dedupe_confidence: float = 0.99,
    risk_flags: list[str] | None = None,
    source_key: str | None = None,
    title: str = "Moderation Candidate",
    organization_name: str = "Example University",
    tags: list[str] | None = None,
    application_url: str | None = None,
) -> tuple[str, str]:
    module_id = connector_headers["X-Module-Id"]
    metadata: dict[str, Any] = {"source": "integration-test"}
    if source_key:
        metadata["source_key"] = source_key

    discovery_response = api_client.post(
        "/discoveries",
        json={
            "origin_module_id": module_id,
            "external_id": external_id,
            "discovered_at": datetime.now(timezone.utc).isoformat(),
            "url": f"https://example.edu/jobs/{external_id}",
            "title_hint": "Moderation Candidate",
            "text_hint": "Moderation flow candidate",
            "metadata": metadata,
        },
        headers=connector_headers,
    )
    assert discovery_response.status_code == 202
    discovery_id = discovery_response.json()["discovery_id"]

    jobs_response = api_client.get("/jobs", headers=PROCESSOR_HEADERS)
    assert jobs_response.status_code == 200
    jobs = jobs_response.json()
    assert len(jobs) == 1
    job_id = jobs[0]["id"]

    claim_response = api_client.post(
        f"/jobs/{job_id}/claim",
        json={"lease_seconds": 120},
        headers=PROCESSOR_HEADERS,
    )
    assert claim_response.status_code == 200

    result_response = api_client.post(
        f"/jobs/{job_id}/result",
        json={
            "status": "done",
            "result_json": {
                "dedupe_confidence": dedupe_confidence,
                "risk_flags": risk_flags or [],
                "source_key": source_key,
                "posting": {
                    "title": title,
                    "organization_name": organization_name,
                    "canonical_url": f"https://example.edu/jobs/{external_id}",
                    "normalized_url": f"https://example.edu/jobs/{external_id}",
                    "canonical_hash": canonical_hash,
                    "country": "US",
                    "remote": True,
                    "tags": tags or ["ml"],
                    "application_url": application_url,
                    "source_refs": [{"kind": "discovery", "id": discovery_id}],
                }
            },
        },
        headers=PROCESSOR_HEADERS,
    )
    assert result_response.status_code == 200
    assert result_response.json()["status"] == "done"

    candidate_id = _run(
        _fetchval(
            database_url,
            """
            select pc.id::text
            from posting_candidates pc
            join candidate_discoveries cd on cd.candidate_id = pc.id
            where cd.discovery_id = $1::uuid
            """,
            discovery_id,
        )
    )
    posting_id = _run(
        _fetchval(
            database_url,
            "select id::text from postings where canonical_hash = $1",
            canonical_hash,
        )
    )
    assert candidate_id
    assert posting_id
    return candidate_id, posting_id


async def _insert_candidate_and_posting(
    database_url: str,
    *,
    canonical_hash: str,
    status: str,
    candidate_state: str,
) -> tuple[str, str]:
    conn = await asyncpg.connect(database_url)
    try:
        candidate_id = await conn.fetchval(
            """
            insert into posting_candidates (
              state,
              dedupe_bucket_key,
              extracted_fields
            )
            values ($1::candidate_state, $2, '{}'::jsonb)
            returning id::text
            """,
            candidate_state,
            canonical_hash,
        )
        posting_id = await conn.fetchval(
            """
            insert into postings (
              candidate_id,
              title,
              canonical_url,
              normalized_url,
              canonical_hash,
              organization_name,
              status,
              published_at,
              created_at,
              updated_at
            )
            values (
              $1::uuid,
              'Freshness Candidate',
              $2,
              $2,
              $3,
              'Example University',
              $4::posting_status,
              now() - interval '3 days',
              now() - interval '3 days',
              now() - interval '3 days'
            )
            returning id::text
            """,
            candidate_id,
            f"https://example.edu/jobs/{canonical_hash}",
            canonical_hash,
            status,
        )
        return candidate_id, posting_id
    finally:
        await conn.close()


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


async def _ensure_connector_module(database_url: str, *, module_id: str, trust_level: str) -> None:
    conn = await asyncpg.connect(database_url)
    try:
        await conn.execute(
            """
            insert into modules (module_id, name, kind, enabled, scopes, trust_level)
            values ($1, $2, 'connector', true, array['discoveries:write', 'evidence:write'], $3::module_trust_level)
            on conflict (module_id)
            do update set
              name = excluded.name,
              kind = excluded.kind,
              enabled = excluded.enabled,
              scopes = excluded.scopes,
              trust_level = excluded.trust_level
            """,
            module_id,
            f"{module_id} test module",
            trust_level,
        )
        await conn.execute(
            """
            insert into module_credentials (module_id, key_hint, key_hash, is_active)
            select id, $2, $3, true
            from modules
            where module_id = $1
            on conflict (module_id, key_hint)
            do update set
              key_hash = excluded.key_hash,
              is_active = true,
              revoked_at = null
            """,
            module_id,
            module_id,
            LOCAL_CONNECTOR_KEY_HASH,
        )
    finally:
        await conn.close()


async def _upsert_source_trust_policy(
    database_url: str,
    *,
    source_key: str,
    trust_level: str,
    auto_publish: bool,
    requires_moderation: bool,
    rules_json: dict[str, Any],
) -> None:
    conn = await asyncpg.connect(database_url)
    try:
        await conn.execute(
            """
            insert into source_trust_policy (
              source_key,
              trust_level,
              auto_publish,
              requires_moderation,
              rules_json,
              enabled
            )
            values ($1, $2::module_trust_level, $3, $4, $5::jsonb, true)
            on conflict (source_key)
            do update set
              trust_level = excluded.trust_level,
              auto_publish = excluded.auto_publish,
              requires_moderation = excluded.requires_moderation,
              rules_json = excluded.rules_json,
              enabled = true
            """,
            source_key,
            trust_level,
            auto_publish,
            requires_moderation,
            json.dumps(rules_json),
        )
    finally:
        await conn.close()


async def _fetchval(database_url: str, query: str, *args: Any) -> Any:
    conn = await asyncpg.connect(database_url)
    try:
        return await conn.fetchval(query, *args)
    finally:
        await conn.close()


async def _execute(database_url: str, query: str, *args: Any) -> None:
    conn = await asyncpg.connect(database_url)
    try:
        await conn.execute(query, *args)
    finally:
        await conn.close()
