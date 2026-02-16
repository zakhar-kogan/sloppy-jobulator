from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import get_settings
from app.core.security import get_machine_principal
from app.core.urls import canonical_hash, normalize_url, parse_normalization_overrides
from app.schemas.discoveries import DiscoveryAccepted, DiscoveryEvent
from app.services.repository import (
    RepositoryConflictError,
    RepositoryUnavailableError,
    get_repository,
)

router = APIRouter()


@router.post("", response_model=DiscoveryAccepted, status_code=status.HTTP_202_ACCEPTED)
async def create_discovery(
    payload: DiscoveryEvent,
    principal=Depends(get_machine_principal),
    repository=Depends(get_repository),
) -> DiscoveryAccepted:
    try:
        principal.require_scopes({"discoveries:write"})
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    if not payload.url:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="url is required in 80/20 ingestion mode",
        )

    normalization_overrides_json: str | None = None
    try:
        normalization_overrides_json = await repository.get_enabled_url_normalization_overrides_json()
    except RepositoryUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    settings = get_settings()

    normalization_overrides = parse_normalization_overrides(normalization_overrides_json)
    if not principal.actor_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid machine principal")
    if payload.origin_module_id != principal.subject:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="origin_module_id must match authenticated module",
        )

    normalized = normalize_url(payload.url, overrides=normalization_overrides) if payload.url else None
    hashed = canonical_hash(normalized) if normalized else None
    enqueue_redirect_resolution = bool(payload.url) and _resolve_redirect_preference(
        payload.metadata,
        default_enabled=settings.enable_redirect_resolution_jobs,
    )

    try:
        discovery_id = await repository.create_discovery_and_enqueue_extract(
            origin_module_db_id=principal.actor_id,
            external_id=payload.external_id,
            discovered_at=payload.discovered_at,
            url=payload.url,
            normalized_url=normalized,
            canonical_hash=hashed,
            title_hint=payload.title_hint,
            text_hint=payload.text_hint,
            metadata=payload.metadata,
            actor_module_db_id=principal.actor_id,
            enqueue_redirect_resolution=enqueue_redirect_resolution,
        )
    except RepositoryUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except RepositoryConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return DiscoveryAccepted(
        discovery_id=discovery_id,
        normalized_url=normalized,
        canonical_hash=hashed,
    )


def _resolve_redirect_preference(metadata: dict[str, object], *, default_enabled: bool) -> bool:
    raw = metadata.get("resolve_redirects")
    if raw is None:
        return default_enabled
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, (int, float)):
        return bool(raw)
    if isinstance(raw, str):
        lowered = raw.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return default_enabled
