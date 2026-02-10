from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal
from urllib.parse import urlparse

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@([A-Z0-9.-]+\.[A-Z]{2,})\b", re.IGNORECASE)
_STOP_WORDS = {
    "a",
    "an",
    "and",
    "at",
    "for",
    "from",
    "in",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
}

MergeDecision = Literal["none", "auto_merged", "needs_review", "rejected"]


@dataclass(slots=True)
class NamedEntities:
    organizations: list[str]
    locations: list[str]
    people: list[str]


@dataclass(slots=True)
class DedupeCandidateSnapshot:
    candidate_id: str
    canonical_hash: str | None
    normalized_url: str | None
    canonical_url: str | None
    application_url: str | None
    title: str | None
    organization_name: str | None
    description_text: str | None
    tags: list[str]
    areas: list[str]
    country: str | None
    region: str | None
    city: str | None
    named_entities: NamedEntities
    contact_domains: list[str]
    has_posting: bool


@dataclass(slots=True)
class DedupeScore:
    candidate_id: str
    confidence: float
    strong_signals: list[str]
    risk_flags: list[str]
    has_posting: bool
    components: dict[str, float]


@dataclass(slots=True)
class DedupePolicyDecision:
    decision: MergeDecision
    primary_candidate_id: str | None
    confidence: float | None
    risk_flags: list[str]
    metadata: dict[str, Any]


def evaluate_merge_policy(
    *,
    incoming: DedupeCandidateSnapshot,
    existing: list[DedupeCandidateSnapshot],
    auto_merge_threshold: float = 0.93,
    review_threshold: float = 0.72,
    ambiguity_delta: float = 0.03,
) -> DedupePolicyDecision:
    scores = [score_candidate_pair(incoming=incoming, existing=row) for row in existing]
    if not scores:
        return DedupePolicyDecision(
            decision="none",
            primary_candidate_id=None,
            confidence=None,
            risk_flags=[],
            metadata={"reason": "no_merge_candidates"},
        )

    ranked = sorted(scores, key=lambda row: (-row.confidence, row.candidate_id))
    best = ranked[0]
    merged_flags = list(best.risk_flags)

    if len(ranked) > 1:
        second = ranked[1]
        if second.confidence >= review_threshold and abs(best.confidence - second.confidence) <= ambiguity_delta:
            merged_flags.append("conflict_multiple_close_matches")

    merged_flags = _dedupe_text_list(merged_flags)
    has_conflict_flag = any(flag.startswith("conflict_") for flag in merged_flags)
    has_strong_signal = bool(best.strong_signals)

    if (
        best.confidence >= auto_merge_threshold
        and has_strong_signal
        and best.has_posting
        and not has_conflict_flag
    ):
        decision: MergeDecision = "auto_merged"
    elif best.confidence >= review_threshold or has_conflict_flag:
        decision = "needs_review"
    elif has_strong_signal:
        decision = "rejected"
    else:
        decision = "none"

    return DedupePolicyDecision(
        decision=decision,
        primary_candidate_id=best.candidate_id if decision != "none" else None,
        confidence=round(best.confidence, 4),
        risk_flags=merged_flags,
        metadata={
            "auto_merge_threshold": auto_merge_threshold,
            "review_threshold": review_threshold,
            "ambiguity_delta": ambiguity_delta,
            "selected_candidate_id": best.candidate_id,
            "selected_components": best.components,
            "selected_strong_signals": list(best.strong_signals),
            "selected_risk_flags": list(best.risk_flags),
            "ranked_candidates": [
                {
                    "candidate_id": row.candidate_id,
                    "confidence": round(row.confidence, 4),
                    "strong_signals": list(row.strong_signals),
                    "risk_flags": list(row.risk_flags),
                }
                for row in ranked[:3]
            ],
        },
    )


def score_candidate_pair(
    *,
    incoming: DedupeCandidateSnapshot,
    existing: DedupeCandidateSnapshot,
) -> DedupeScore:
    strong_signals: list[str] = []
    score = 0.0

    if _equals(incoming.canonical_hash, existing.canonical_hash):
        strong_signals.append("canonical_hash")
        score += 0.65
    if _equals(incoming.normalized_url, existing.normalized_url):
        strong_signals.append("normalized_url")
        score += 0.20
    if _equals(incoming.canonical_url, existing.canonical_url):
        strong_signals.append("canonical_url")
        score += 0.15
    if _equals(incoming.application_url, existing.application_url):
        strong_signals.append("application_url")
        score += 0.10

    title_similarity = _jaccard(_tokenize(incoming.title), _tokenize(existing.title))
    organization_similarity = _organization_similarity(incoming.organization_name, existing.organization_name)
    phrase_similarity = _jaccard(
        _phrase_tokens(incoming),
        _phrase_tokens(existing),
    )

    medium_score = (0.45 * title_similarity) + (0.25 * organization_similarity) + (0.10 * phrase_similarity)
    score += medium_score

    org_ner_overlap = _jaccard(
        _normalized_set(incoming.named_entities.organizations),
        _normalized_set(existing.named_entities.organizations),
    )
    location_overlap = _jaccard(
        _normalized_set(incoming.named_entities.locations) | _location_set(incoming),
        _normalized_set(existing.named_entities.locations) | _location_set(existing),
    )
    person_overlap = _jaccard(
        _normalized_set(incoming.named_entities.people),
        _normalized_set(existing.named_entities.people),
    )
    domain_overlap = _jaccard(_domain_set(incoming), _domain_set(existing))
    contact_domain_overlap = _jaccard(
        _normalized_set(incoming.contact_domains),
        _normalized_set(existing.contact_domains),
    )

    tie_break_score = (
        (0.10 * org_ner_overlap)
        + (0.05 * location_overlap)
        + (0.05 * person_overlap)
        + (0.05 * domain_overlap)
        + (0.05 * contact_domain_overlap)
    )
    score += tie_break_score

    if not strong_signals:
        score = min(score, 0.89)

    confidence = min(score, 0.9999)
    risk_flags = _score_risk_flags(
        incoming=incoming,
        existing=existing,
        confidence=confidence,
        strong_signals=strong_signals,
        title_similarity=title_similarity,
        organization_similarity=organization_similarity,
    )

    return DedupeScore(
        candidate_id=existing.candidate_id,
        confidence=confidence,
        strong_signals=strong_signals,
        risk_flags=risk_flags,
        has_posting=existing.has_posting,
        components={
            "title_similarity": round(title_similarity, 4),
            "organization_similarity": round(organization_similarity, 4),
            "phrase_similarity": round(phrase_similarity, 4),
            "org_ner_overlap": round(org_ner_overlap, 4),
            "location_overlap": round(location_overlap, 4),
            "person_overlap": round(person_overlap, 4),
            "domain_overlap": round(domain_overlap, 4),
            "contact_domain_overlap": round(contact_domain_overlap, 4),
            "medium_score": round(medium_score, 4),
            "tie_break_score": round(tie_break_score, 4),
        },
    )


def extract_named_entities(payload: Any) -> NamedEntities:
    if not isinstance(payload, dict):
        return NamedEntities(organizations=[], locations=[], people=[])

    raw = payload.get("ner") or payload.get("named_entities") or payload.get("entities")
    organizations: list[str] = []
    locations: list[str] = []
    people: list[str] = []

    if isinstance(raw, dict):
        organizations.extend(_text_values(raw.get("org")))
        organizations.extend(_text_values(raw.get("orgs")))
        organizations.extend(_text_values(raw.get("organization")))
        organizations.extend(_text_values(raw.get("organizations")))
        locations.extend(_text_values(raw.get("location")))
        locations.extend(_text_values(raw.get("locations")))
        locations.extend(_text_values(raw.get("place")))
        locations.extend(_text_values(raw.get("places")))
        people.extend(_text_values(raw.get("person")))
        people.extend(_text_values(raw.get("people")))
        people.extend(_text_values(raw.get("persons")))
    elif isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            label = _coerce_text(item.get("type")) or _coerce_text(item.get("label")) or ""
            value = _coerce_text(item.get("text")) or _coerce_text(item.get("value"))
            if not value:
                continue
            normalized_label = label.strip().upper()
            if normalized_label in {"ORG", "ORGANIZATION"}:
                organizations.append(value)
            elif normalized_label in {"LOC", "LOCATION", "GPE"}:
                locations.append(value)
            elif normalized_label in {"PERSON", "PER"}:
                people.append(value)

    return NamedEntities(
        organizations=_dedupe_text_list(organizations),
        locations=_dedupe_text_list(locations),
        people=_dedupe_text_list(people),
    )


def extract_contact_domains(payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        return []
    candidates: list[str] = []
    for key in ("contact_email", "contact_emails", "email", "emails", "contact"):
        candidates.extend(_text_values(payload.get(key)))
    domains = [domain.lower() for candidate in candidates for domain in _EMAIL_RE.findall(candidate)]
    return _dedupe_text_list(domains)


def _score_risk_flags(
    *,
    incoming: DedupeCandidateSnapshot,
    existing: DedupeCandidateSnapshot,
    confidence: float,
    strong_signals: list[str],
    title_similarity: float,
    organization_similarity: float,
) -> list[str]:
    risk_flags: list[str] = []
    if not strong_signals and confidence >= 0.72:
        risk_flags.append("manual_review_low_signal")

    if (
        incoming.canonical_hash
        and existing.canonical_hash
        and incoming.canonical_hash != existing.canonical_hash
        and (_equals(incoming.normalized_url, existing.normalized_url) or _equals(incoming.canonical_url, existing.canonical_url))
    ):
        risk_flags.append("conflict_hash_mismatch")

    if strong_signals and incoming.organization_name and existing.organization_name and organization_similarity < 0.25:
        risk_flags.append("conflict_organization_mismatch")
    if strong_signals and incoming.title and existing.title and title_similarity < 0.25:
        risk_flags.append("conflict_title_mismatch")
    if (
        incoming.application_url
        and existing.application_url
        and incoming.application_url != existing.application_url
        and strong_signals
    ):
        risk_flags.append("conflict_application_url_mismatch")

    return _dedupe_text_list(risk_flags)


def _equals(left: str | None, right: str | None) -> bool:
    return bool(left and right and left == right)


def _phrase_tokens(candidate: DedupeCandidateSnapshot) -> set[str]:
    terms: list[str] = []
    terms.extend(candidate.tags)
    terms.extend(candidate.areas)
    if candidate.description_text:
        terms.append(candidate.description_text)
    return _tokenize(" ".join(terms))


def _organization_similarity(left: str | None, right: str | None) -> float:
    if not left or not right:
        return 0.0
    if left.casefold() == right.casefold():
        return 1.0
    return _jaccard(_tokenize(left), _tokenize(right))


def _location_set(candidate: DedupeCandidateSnapshot) -> set[str]:
    return _normalized_set([candidate.country or "", candidate.region or "", candidate.city or ""])


def _domain_set(candidate: DedupeCandidateSnapshot) -> set[str]:
    domains = []
    for raw in (candidate.canonical_url, candidate.normalized_url, candidate.application_url):
        parsed = _parse_host(raw)
        if parsed:
            domains.append(parsed)
    return _normalized_set(domains)


def _parse_host(raw_url: str | None) -> str | None:
    if not raw_url:
        return None
    parsed = urlparse(raw_url)
    host = parsed.hostname
    if not host:
        return None
    normalized = host.strip().lower()
    return normalized or None


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    intersection = len(left & right)
    union = len(left | right)
    if union <= 0:
        return 0.0
    return intersection / union


def _normalized_set(values: list[str]) -> set[str]:
    return {value.casefold() for value in values if value}


def _tokenize(value: str | None) -> set[str]:
    if not value:
        return set()
    tokens = _TOKEN_RE.findall(value.casefold())
    return {token for token in tokens if token and token not in _STOP_WORDS}


def _coerce_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return str(value)


def _text_values(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    if isinstance(value, list):
        items: list[str] = []
        for entry in value:
            if isinstance(entry, str):
                stripped = entry.strip()
                if stripped:
                    items.append(stripped)
        return items
    return []


def _dedupe_text_list(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        stripped = value.strip()
        if not stripped:
            continue
        key = stripped.casefold()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(stripped)
    return deduped
