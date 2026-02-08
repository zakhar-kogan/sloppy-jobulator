from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import get_machine_principal
from app.schemas.evidence import EvidenceAccepted, EvidenceIn
from app.services.repository import (
    RepositoryConflictError,
    RepositoryUnavailableError,
    get_repository,
)

router = APIRouter()


@router.post("", response_model=EvidenceAccepted, status_code=status.HTTP_202_ACCEPTED)
async def create_evidence(
    payload: EvidenceIn,
    principal=Depends(get_machine_principal),
    repository=Depends(get_repository),
) -> EvidenceAccepted:
    try:
        principal.require_scopes({"evidence:write"})
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    if not principal.actor_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid machine principal")

    try:
        evidence_id = await repository.create_evidence(
            discovery_id=payload.discovery_id,
            kind=payload.kind,
            uri=payload.uri,
            content_hash=payload.content_hash,
            captured_at=payload.captured_at,
            content_type=payload.content_type,
            byte_size=payload.byte_size,
            metadata=payload.metadata,
            actor_module_db_id=principal.actor_id,
        )
    except RepositoryUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except RepositoryConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return EvidenceAccepted(evidence_id=evidence_id)
