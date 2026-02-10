from app.services.dedupe import (
    DedupeCandidateSnapshot,
    NamedEntities,
    evaluate_merge_policy,
)


def test_evaluate_merge_policy_auto_merges_high_confidence_strong_match() -> None:
    incoming = _snapshot(
        candidate_id="incoming",
        canonical_hash="hash-123",
        normalized_url="https://example.edu/jobs/a",
        canonical_url="https://example.edu/jobs/a",
        title="Research Scientist",
        organization_name="Example University",
        description_text="Machine learning for biology",
    )
    existing = [
        _snapshot(
            candidate_id="existing-1",
            canonical_hash="hash-123",
            normalized_url="https://example.edu/jobs/a",
            canonical_url="https://example.edu/jobs/a",
            title="Research Scientist",
            organization_name="Example University",
            description_text="Machine learning for biology",
        )
    ]

    decision = evaluate_merge_policy(incoming=incoming, existing=existing)

    assert decision.decision == "auto_merged"
    assert decision.primary_candidate_id == "existing-1"
    assert decision.confidence is not None and decision.confidence >= 0.93


def test_evaluate_merge_policy_routes_text_only_duplicates_to_review() -> None:
    incoming = _snapshot(
        candidate_id="incoming",
        canonical_hash="hash-new",
        normalized_url="https://example.edu/jobs/new",
        canonical_url="https://example.edu/jobs/new",
        title="Postdoctoral Fellow in Bioinformatics",
        organization_name="Example University",
        description_text="Genomics and machine learning in translational medicine",
    )
    existing = [
        _snapshot(
            candidate_id="existing-1",
            canonical_hash="hash-old",
            normalized_url="https://example.edu/jobs/old",
            canonical_url="https://example.edu/jobs/old",
            title="Postdoctoral Fellow in Bioinformatics",
            organization_name="Example University",
            description_text="Genomics and machine learning in translational medicine",
        )
    ]

    decision = evaluate_merge_policy(incoming=incoming, existing=existing)

    assert decision.decision == "needs_review"
    assert decision.primary_candidate_id == "existing-1"
    assert "manual_review_low_signal" in decision.risk_flags


def test_evaluate_merge_policy_blocks_auto_merge_on_conflict_flags() -> None:
    incoming = _snapshot(
        candidate_id="incoming",
        canonical_hash="hash-123",
        normalized_url="https://example.edu/jobs/a",
        canonical_url="https://example.edu/jobs/a",
        title="AI Research Engineer",
        organization_name="Org One",
        description_text="Research role",
    )
    existing = [
        _snapshot(
            candidate_id="existing-1",
            canonical_hash="hash-123",
            normalized_url="https://example.edu/jobs/a",
            canonical_url="https://example.edu/jobs/a",
            title="Assistant Professor in History",
            organization_name="Org Two",
            description_text="Humanities role",
        )
    ]

    decision = evaluate_merge_policy(incoming=incoming, existing=existing)

    assert decision.decision == "needs_review"
    assert any(flag.startswith("conflict_") for flag in decision.risk_flags)


def test_evaluate_merge_policy_returns_none_when_no_candidates() -> None:
    incoming = _snapshot(
        candidate_id="incoming",
        canonical_hash="hash-123",
        normalized_url="https://example.edu/jobs/a",
        canonical_url="https://example.edu/jobs/a",
        title="Research Scientist",
        organization_name="Example University",
        description_text="Machine learning for biology",
    )

    decision = evaluate_merge_policy(incoming=incoming, existing=[])

    assert decision.decision == "none"
    assert decision.primary_candidate_id is None
    assert decision.confidence is None


def _snapshot(
    *,
    candidate_id: str,
    canonical_hash: str,
    normalized_url: str,
    canonical_url: str,
    title: str,
    organization_name: str,
    description_text: str,
) -> DedupeCandidateSnapshot:
    return DedupeCandidateSnapshot(
        candidate_id=candidate_id,
        canonical_hash=canonical_hash,
        normalized_url=normalized_url,
        canonical_url=canonical_url,
        application_url=None,
        title=title,
        organization_name=organization_name,
        description_text=description_text,
        tags=["ml", "genomics"],
        areas=["biology"],
        country="US",
        region="CA",
        city="San Francisco",
        named_entities=NamedEntities(
            organizations=[organization_name],
            locations=["San Francisco"],
            people=[],
        ),
        contact_domains=["example.edu"],
        has_posting=True,
    )
