from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.security import get_human_principal
from app.schemas.candidates import CandidateOut, CandidatePatchRequest, CandidateState
from app.services.repository import (
    RepositoryConflictError,
    RepositoryNotFoundError,
    RepositoryUnavailableError,
    get_repository,
)

router = APIRouter()


@router.get("", response_model=list[CandidateOut])
async def list_candidates(
    principal=Depends(get_human_principal),
    repository=Depends(get_repository),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    state: CandidateState | None = Query(default=None),
) -> list[CandidateOut]:
    try:
        principal.require_scopes({"moderation:read"})
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    try:
        rows = await repository.list_candidates(limit=limit, offset=offset, state=state)
    except RepositoryUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return [CandidateOut(**row) for row in rows]


@router.patch("/{candidate_id}", response_model=CandidateOut)
async def patch_candidate(
    candidate_id: str,
    payload: CandidatePatchRequest,
    principal=Depends(get_human_principal),
    repository=Depends(get_repository),
) -> CandidateOut:
    try:
        principal.require_scopes({"moderation:write"})
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    if not principal.actor_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid human principal")

    try:
        row = await repository.update_candidate_state(
            candidate_id=candidate_id,
            state=payload.state,
            actor_user_id=principal.actor_id,
            reason=payload.reason,
        )
    except RepositoryUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except RepositoryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RepositoryConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return CandidateOut(**row)
