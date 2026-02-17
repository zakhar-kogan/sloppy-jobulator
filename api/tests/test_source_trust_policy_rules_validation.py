from __future__ import annotations

import pytest

from app.services.repository import PostgresRepository, RepositoryValidationError


def _repository() -> PostgresRepository:
    return PostgresRepository(
        database_url=None,
        min_pool_size=1,
        max_pool_size=1,
        job_max_attempts=3,
        job_retry_base_seconds=1,
        job_retry_max_seconds=60,
        freshness_check_interval_hours=24,
        freshness_stale_after_hours=24,
        freshness_archive_after_hours=72,
    )


def test_source_trust_policy_rules_accepts_advanced_keys_but_sanitizes_to_simple_profile() -> None:
    repository = _repository()

    normalized = repository._validate_source_trust_policy_rules_json(
        {
            "min_confidence": 0.0,
            "merge_decision_actions": {"needs_review": "reject"},
            "merge_decision_reasons": {"needs_review": "policy_merge_needs_review_reject"},
            "moderation_routes": {"needs_review": "dedupe.manual_triage"},
        },
        strict=True,
    )

    assert normalized == {"min_confidence": 0.0}


def test_source_trust_policy_rules_rejects_unknown_merge_decision_key() -> None:
    repository = _repository()

    with pytest.raises(RepositoryValidationError, match="unsupported keys: merge_decision_actions"):
        repository._validate_source_trust_policy_rules_json(
            {
                "merge_decision_actions": {"unknown_decision": "reject"},
            },
            strict=True,
        )


def test_source_trust_policy_rules_rejects_invalid_moderation_route_label() -> None:
    repository = _repository()

    with pytest.raises(RepositoryValidationError, match="unsupported keys: moderation_routes"):
        repository._validate_source_trust_policy_rules_json(
            {
                "moderation_routes": {"needs_review": "Dedupe Manual Queue"},
            },
            strict=True,
        )
