from app.core.urls import normalize_url, parse_normalization_overrides


def test_normalize_url_applies_domain_overrides() -> None:
    overrides = parse_normalization_overrides(
        '{"example.edu":{"strip_query_params":["sessionid"],"strip_www":true,"force_https":true}}'
    )
    normalized = normalize_url(
        "http://www.example.edu/jobs/role/?utm_source=feed&sessionId=abc",
        overrides=overrides,
    )
    assert normalized == "https://example.edu/jobs/role"


def test_normalize_url_keeps_default_behavior_without_overrides() -> None:
    normalized = normalize_url("https://Example.edu/jobs/role/?utm_source=feed&lang=en")
    assert normalized == "https://example.edu/jobs/role?lang=en"
