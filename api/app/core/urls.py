import hashlib
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

TRACKING_KEYS = {"ref", "fbclid", "gclid"}


def _is_tracking_param(key: str) -> bool:
    return key.startswith("utm_") or key in TRACKING_KEYS


def normalize_url(raw_url: str) -> str:
    """Conservative URL normalization used for idempotency and dedupe seeds."""
    parsed = urlparse(raw_url.strip())

    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    if ":" in netloc:
        host, port = netloc.rsplit(":", maxsplit=1)
        if (scheme == "http" and port == "80") or (scheme == "https" and port == "443"):
            netloc = host

    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path[:-1]

    filtered_query_pairs = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not _is_tracking_param(key)
    ]
    filtered_query_pairs.sort(key=lambda pair: pair[0])
    query = urlencode(filtered_query_pairs, doseq=True)

    return urlunparse((scheme, netloc, path, "", query, ""))


def canonical_hash(normalized_url: str) -> str:
    return hashlib.sha256(normalized_url.encode("utf-8")).hexdigest()
