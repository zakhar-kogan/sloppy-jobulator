from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import get_machine_principal
from app.schemas.evidence import EvidenceAccepted, EvidenceIn
from app.services.store import STORE

router = APIRouter()


@router.post("", response_model=EvidenceAccepted, status_code=status.HTTP_202_ACCEPTED)
async def create_evidence(payload: EvidenceIn, principal=Depends(get_machine_principal)) -> EvidenceAccepted:
    try:
        principal.require_scopes({"evidence:write"})
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    evidence_id = str(uuid4())
    STORE.evidence[evidence_id] = payload.model_dump() | {"id": evidence_id, "ingested_by": principal.subject}
    return EvidenceAccepted(evidence_id=evidence_id)
