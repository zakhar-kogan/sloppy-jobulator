from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.security import get_human_principal
from app.schemas.candidates import (
    CandidateAgeBucket,
    CandidateEventOut,
    CandidateFacetsOut,
    CandidateMergeRequest,
    CandidateOverrideRequest,
    CandidateOut,
    CandidatePatchRequest,
    CandidateState,
)
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
    source: str | None = Query(default=None, min_length=1, max_length=200),
    age: CandidateAgeBucket | None = Query(default=None),
) -> list[CandidateOut]:
    try:
        principal.require_scopes({"moderation:read"})
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    try:
        rows = await repository.list_candidates(limit=limit, offset=offset, state=state, source=source, age=age)
    except RepositoryUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return [CandidateOut(**row) for row in rows]


@router.get("/facets", response_model=CandidateFacetsOut)
async def list_candidate_facets(
    principal=Depends(get_human_principal),
    repository=Depends(get_repository),
    state: CandidateState | None = Query(default=None),
    source: str | None = Query(default=None, min_length=1, max_length=200),
    age: CandidateAgeBucket | None = Query(default=None),
) -> CandidateFacetsOut:
    try:
        principal.require_scopes({"moderation:read"})
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    try:
        facets = await repository.list_candidate_facets(state=state, source=source, age=age)
    except RepositoryUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return CandidateFacetsOut(**facets)


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


@router.post("/{candidate_id}/merge", response_model=CandidateOut)
async def merge_candidate(
    candidate_id: str,
    payload: CandidateMergeRequest,
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
        row = await repository.merge_candidates(
            primary_candidate_id=candidate_id,
            secondary_candidate_id=payload.secondary_candidate_id,
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


@router.post("/{candidate_id}/override", response_model=CandidateOut)
async def override_candidate(
    candidate_id: str,
    payload: CandidateOverrideRequest,
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
        row = await repository.override_candidate_state(
            candidate_id=candidate_id,
            state=payload.state,
            actor_user_id=principal.actor_id,
            reason=payload.reason,
            posting_status=payload.posting_status,
        )
    except RepositoryUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except RepositoryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RepositoryConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return CandidateOut(**row)


@router.get("/{candidate_id}/events", response_model=list[CandidateEventOut])
async def list_candidate_events(
    candidate_id: str,
    principal=Depends(get_human_principal),
    repository=Depends(get_repository),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[CandidateEventOut]:
    try:
        principal.require_scopes({"moderation:read"})
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    try:
        rows = await repository.list_candidate_events(candidate_id=candidate_id, limit=limit, offset=offset)
    except RepositoryUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except RepositoryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RepositoryConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return [CandidateEventOut(**row) for row in rows]
