from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import get_machine_principal
from app.core.urls import canonical_hash, normalize_url
from app.schemas.discoveries import DiscoveryAccepted, DiscoveryEvent
from app.services.store import STORE

router = APIRouter()


@router.post("", response_model=DiscoveryAccepted, status_code=status.HTTP_202_ACCEPTED)
async def create_discovery(
    payload: DiscoveryEvent,
    principal=Depends(get_machine_principal),
) -> DiscoveryAccepted:
    try:
        principal.require_scopes({"discoveries:write"})
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    normalized = normalize_url(payload.url) if payload.url else None
    hashed = canonical_hash(normalized) if normalized else None

    discovery_id = str(uuid4())
    STORE.discoveries[discovery_id] = {
        "id": discovery_id,
        "origin_module_id": payload.origin_module_id,
        "external_id": payload.external_id,
        "discovered_at": payload.discovered_at,
        "url": payload.url,
        "normalized_url": normalized,
        "canonical_hash": hashed,
        "title_hint": payload.title_hint,
        "text_hint": payload.text_hint,
        "metadata": payload.metadata,
        "ingested_by": principal.subject,
    }

    STORE.enqueue_job(
        kind="extract",
        target_type="discovery",
        target_id=discovery_id,
        inputs={"discovery_id": discovery_id},
    )

    return DiscoveryAccepted(
        discovery_id=discovery_id,
        normalized_url=normalized,
        canonical_hash=hashed,
    )
