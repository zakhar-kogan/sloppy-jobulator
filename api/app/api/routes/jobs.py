from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import get_machine_principal
from app.schemas.jobs import ClaimRequest, JobOut, ResultRequest
from app.services.store import STORE

router = APIRouter()


@router.get("", response_model=list[JobOut])
async def get_jobs(principal=Depends(get_machine_principal), limit: int = 20) -> list[JobOut]:
    try:
        principal.require_scopes({"jobs:read"})
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    queued = [STORE.jobs[job_id] for job_id in list(STORE.job_queue)[:limit]]
    return [JobOut(**job) for job in queued]


@router.post("/{job_id}/claim", response_model=JobOut)
async def claim_job(job_id: str, payload: ClaimRequest, principal=Depends(get_machine_principal)) -> JobOut:
    try:
        principal.require_scopes({"jobs:write"})
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    job = STORE.jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")

    if job["status"] != "queued":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="job is not claimable")

    job["status"] = "claimed"
    job["locked_by_module_id"] = principal.subject
    job["locked_at"] = datetime.now(timezone.utc)
    job["lease_expires_at"] = datetime.now(timezone.utc) + timedelta(seconds=payload.lease_seconds)

    if STORE.job_queue and STORE.job_queue[0] == job_id:
        STORE.job_queue.popleft()

    return JobOut(**job)


@router.post("/{job_id}/result", response_model=JobOut)
async def submit_job_result(job_id: str, payload: ResultRequest, principal=Depends(get_machine_principal)) -> JobOut:
    try:
        principal.require_scopes({"jobs:write"})
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    job = STORE.jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")

    if job.get("locked_by_module_id") != principal.subject:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="job claimed by another module")

    if payload.status not in {"done", "failed", "dead_letter"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid terminal status")

    job["status"] = payload.status
    job["result_json"] = payload.result_json
    job["error_json"] = payload.error_json
    return JobOut(**job)
