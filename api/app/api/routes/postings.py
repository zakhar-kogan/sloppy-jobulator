from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status

from app.core.security import get_human_principal
from app.schemas.postings import PostingDetailOut, PostingListOut, PostingPatchRequest, PostingSortBy, PostingStatus, SortDir
from app.services.repository import (
    RepositoryConflictError,
    RepositoryNotFoundError,
    RepositoryUnavailableError,
    get_repository,
)

router = APIRouter()


@router.get("", response_model=list[PostingListOut])
async def list_postings(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    q: str | None = Query(default=None, min_length=1),
    organization_name: str | None = Query(default=None, min_length=1),
    country: str | None = Query(default=None, min_length=1),
    remote: bool | None = Query(default=None),
    posting_status: PostingStatus | None = Query(default=None, alias="status"),
    tag: str | None = Query(default=None, min_length=1),
    sort_by: PostingSortBy = Query(default="created_at"),
    sort_dir: SortDir = Query(default="desc"),
    repository=Depends(get_repository),
) -> list[PostingListOut]:
    try:
        rows = await repository.list_postings(
            limit=limit,
            offset=offset,
            q=q,
            organization_name=organization_name,
            country=country,
            remote=remote,
            status=posting_status,
            tag=tag,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
    except RepositoryUnavailableError as exc:
        raise HTTPException(status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return [PostingListOut(**row) for row in rows]


@router.get("/{posting_id}", response_model=PostingDetailOut)
async def get_posting(posting_id: str, repository=Depends(get_repository)) -> PostingDetailOut:
    try:
        row = await repository.get_posting(posting_id=posting_id)
    except RepositoryUnavailableError as exc:
        raise HTTPException(status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except RepositoryNotFoundError as exc:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return PostingDetailOut(**row)


@router.patch("/{posting_id}", response_model=PostingDetailOut)
async def patch_posting(
    posting_id: str,
    payload: PostingPatchRequest,
    principal=Depends(get_human_principal),
    repository=Depends(get_repository),
) -> PostingDetailOut:
    try:
        principal.require_scopes({"moderation:write"})
    except PermissionError as exc:
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    if not principal.actor_id:
        raise HTTPException(status_code=http_status.HTTP_401_UNAUTHORIZED, detail="invalid human principal")

    try:
        row = await repository.update_posting_status(
            posting_id=posting_id,
            status=payload.status,
            actor_user_id=principal.actor_id,
            reason=payload.reason,
        )
    except RepositoryUnavailableError as exc:
        raise HTTPException(status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except RepositoryNotFoundError as exc:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RepositoryConflictError as exc:
        raise HTTPException(status_code=http_status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return PostingDetailOut(**row)
