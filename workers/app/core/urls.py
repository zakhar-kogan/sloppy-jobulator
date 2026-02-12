from __future__ import annotations

import hashlib
import json
from typing import Any, TypedDict
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

TRACKING_KEYS = {"ref", "fbclid", "gclid"}


class URLNormalizationOverride(TypedDict):
    strip_query_params: set[str]
    strip_query_prefixes: set[str]
    strip_www: bool
    force_https: bool


def canonical_hash(normalized_url: str) -> str:
    return hashlib.sha256(normalized_url.encode("utf-8")).hexdigest()


def parse_normalization_overrides(raw: str | None) -> dict[str, URLNormalizationOverride]:
    if not raw:
        return {}
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(decoded, dict):
        return {}

    parsed: dict[str, URLNormalizationOverride] = {}
    for raw_domain, raw_rules in decoded.items():
        if not isinstance(raw_domain, str):
            continue
        domain = raw_domain.strip().lower().lstrip(".")
        if not domain or not isinstance(raw_rules, dict):
            continue

        parsed[domain] = {
            "strip_query_params": _coerce_lower_str_set(raw_rules.get("strip_query_params")),
            "strip_query_prefixes": _coerce_lower_str_set(raw_rules.get("strip_query_prefixes")),
            "strip_www": bool(raw_rules.get("strip_www", False)),
            "force_https": bool(raw_rules.get("force_https", False)),
        }
    return parsed


def normalize_url(raw_url: str, *, overrides: dict[str, URLNormalizationOverride] | None = None) -> str:
    parsed = urlparse(raw_url.strip())

    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    host = netloc
    port = ""
    if ":" in netloc:
        host, port = netloc.rsplit(":", maxsplit=1)
        if (scheme == "http" and port == "80") or (scheme == "https" and port == "443"):
            netloc = host
            port = ""

    override = _match_override(host, overrides or {})
    if override and override["strip_www"] and host.startswith("www."):
        host = host[4:]
        netloc = host if not port else f"{host}:{port}"
    if override and override["force_https"] and scheme == "http":
        scheme = "https"

    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path[:-1]

    filtered_query_pairs = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not _should_strip_query_param(key, override)
    ]
    filtered_query_pairs.sort(key=lambda pair: pair[0])
    query = urlencode(filtered_query_pairs, doseq=True)
    return urlunparse((scheme, netloc, path, "", query, ""))


def _coerce_lower_str_set(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {item.strip().lower() for item in value if isinstance(item, str) and item.strip()}


def _is_tracking_param(key: str) -> bool:
    return key.startswith("utm_") or key in TRACKING_KEYS


def _match_override(host: str, overrides: dict[str, URLNormalizationOverride]) -> URLNormalizationOverride | None:
    if not host or not overrides:
        return None
    labels = host.split(".")
    for index in range(len(labels)):
        candidate = ".".join(labels[index:])
        if candidate in overrides:
            return overrides[candidate]
    return None


def _should_strip_query_param(key: str, override: URLNormalizationOverride | None) -> bool:
    lowered = key.lower()
    if _is_tracking_param(lowered):
        return True
    if not override:
        return False
    if lowered in override["strip_query_params"]:
        return True
    return any(lowered.startswith(prefix) for prefix in override["strip_query_prefixes"])
