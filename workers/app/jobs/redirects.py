from __future__ import annotations

from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from app.core.urls import canonical_hash, normalize_url, parse_normalization_overrides

REDIRECT_STATUS_CODES = {301, 302, 303, 307, 308}
MAX_REDIRECT_HOPS = 10


async def execute_resolve_url_redirects(
    job: dict[str, Any],
    *,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    raw_inputs = job.get("inputs_json")
    inputs: dict[str, Any] = raw_inputs if isinstance(raw_inputs, dict) else {}
    source_url = _as_text(inputs.get("url")) or _as_text(inputs.get("normalized_url"))
    if not source_url:
        return {
            "handled": True,
            "kind": job.get("kind"),
            "target_type": job.get("target_type"),
            "target_id": job.get("target_id"),
            "reason": "missing_url",
            "redirect_hop_count": 0,
        }

    max_hops = _bounded_int(inputs.get("max_hops"), default=MAX_REDIRECT_HOPS, minimum=1, maximum=25)
    overrides = parse_normalization_overrides(_as_text(inputs.get("normalization_overrides_json")))

    if client is not None:
        resolution = await _resolve_redirect_chain(client=client, source_url=source_url, max_hops=max_hops)
    else:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as temp_client:
            resolution = await _resolve_redirect_chain(client=temp_client, source_url=source_url, max_hops=max_hops)

    resolved_url = _as_text(resolution.get("resolved_url")) or source_url
    resolved_normalized_url: str | None = None
    resolved_canonical_hash: str | None = None
    if resolved_url:
        try:
            resolved_normalized_url = normalize_url(resolved_url, overrides=overrides)
            resolved_canonical_hash = canonical_hash(resolved_normalized_url)
        except ValueError:
            resolved_normalized_url = None
            resolved_canonical_hash = None

    return {
        "handled": True,
        "kind": job.get("kind"),
        "target_type": job.get("target_type"),
        "target_id": job.get("target_id"),
        "source_url": source_url,
        "resolved_url": resolved_url,
        "resolved_normalized_url": resolved_normalized_url,
        "resolved_canonical_hash": resolved_canonical_hash,
        "redirect_hop_count": int(resolution["redirect_hop_count"]),
        "redirect_chain": resolution["redirect_chain"],
        "reason": resolution["reason"],
        "final_status_code": resolution["final_status_code"],
    }


async def _resolve_redirect_chain(
    *,
    client: httpx.AsyncClient,
    source_url: str,
    max_hops: int,
) -> dict[str, Any]:
    current_url = source_url
    seen_urls: set[str] = set()
    redirect_chain: list[dict[str, Any]] = []
    final_status_code: int | None = None
    reason = "no_redirect"

    for _ in range(max_hops):
        parsed = urlparse(current_url)
        if parsed.scheme.lower() not in {"http", "https"}:
            reason = "unsupported_scheme"
            break
        if current_url in seen_urls:
            reason = "redirect_loop_detected"
            break
        seen_urls.add(current_url)

        response = await client.get(current_url, headers={"User-Agent": "sloppy-jobulator-redirect-resolver/1.0"})
        final_status_code = int(response.status_code)
        location = response.headers.get("location")
        if response.status_code in REDIRECT_STATUS_CODES and location:
            next_url = urljoin(str(response.url), location)
            redirect_chain.append(
                {
                    "from_url": str(response.url),
                    "to_url": next_url,
                    "status_code": int(response.status_code),
                }
            )
            current_url = next_url
            reason = "redirect_followed"
            continue
        current_url = str(response.url)
        reason = "resolved"
        break
    else:
        reason = "redirect_hop_limit_exceeded"

    return {
        "resolved_url": current_url,
        "redirect_hop_count": len(redirect_chain),
        "redirect_chain": redirect_chain,
        "reason": reason,
        "final_status_code": final_status_code,
    }


def _as_text(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _bounded_int(value: Any, *, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return min(maximum, max(minimum, parsed))
