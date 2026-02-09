from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.security import get_machine_principal
from app.schemas.jobs import ClaimRequest, JobOut, LeaseReapOut, ResultRequest
from app.services.repository import (
    RepositoryConflictError,
    RepositoryForbiddenError,
    RepositoryNotFoundError,
    RepositoryUnavailableError,
    get_repository,
)

router = APIRouter()


@router.get("", response_model=list[JobOut])
async def get_jobs(
    principal=Depends(get_machine_principal),
    repository=Depends(get_repository),
    limit: int = 20,
) -> list[JobOut]:
    try:
        principal.require_scopes({"jobs:read"})
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    try:
        queued = await repository.list_queued_jobs(limit=limit)
    except RepositoryUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return [JobOut(**job) for job in queued]


@router.post("/{job_id}/claim", response_model=JobOut)
async def claim_job(
    job_id: str,
    payload: ClaimRequest,
    principal=Depends(get_machine_principal),
    repository=Depends(get_repository),
) -> JobOut:
    try:
        principal.require_scopes({"jobs:write"})
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    if not principal.actor_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid machine principal")

    try:
        claimed = await repository.claim_job(job_id=job_id, module_db_id=principal.actor_id, lease_seconds=payload.lease_seconds)
        return JobOut(**claimed)
    except RepositoryUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except RepositoryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RepositoryConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/{job_id}/result", response_model=JobOut)
async def submit_job_result(
    job_id: str,
    payload: ResultRequest,
    principal=Depends(get_machine_principal),
    repository=Depends(get_repository),
) -> JobOut:
    try:
        principal.require_scopes({"jobs:write"})
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    if payload.status not in {"done", "failed", "dead_letter"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid terminal status")

    if not principal.actor_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid machine principal")

    try:
        updated = await repository.submit_job_result(
            job_id=job_id,
            module_db_id=principal.actor_id,
            status=payload.status,
            result_json=payload.result_json,
            error_json=payload.error_json,
        )
        return JobOut(**updated)
    except RepositoryUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except RepositoryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RepositoryForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except RepositoryConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/reap-expired", response_model=LeaseReapOut)
async def reap_expired_jobs(
    principal=Depends(get_machine_principal),
    repository=Depends(get_repository),
    limit: int = Query(default=100, ge=1, le=1000),
) -> LeaseReapOut:
    try:
        principal.require_scopes({"jobs:write"})
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    if not principal.actor_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid machine principal")

    try:
        requeued = await repository.requeue_expired_claimed_jobs(module_db_id=principal.actor_id, limit=limit)
    except RepositoryUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return LeaseReapOut(requeued=requeued)
