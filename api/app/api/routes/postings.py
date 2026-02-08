from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.schemas.postings import PostingOut
from app.services.repository import RepositoryUnavailableError, get_repository

router = APIRouter()


@router.get("", response_model=list[PostingOut])
async def list_postings(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    repository=Depends(get_repository),
) -> list[PostingOut]:
    try:
        rows = await repository.list_postings(limit=limit, offset=offset)
    except RepositoryUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return [PostingOut(**row) for row in rows]
