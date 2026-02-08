from fastapi import APIRouter, Query

from app.schemas.postings import PostingOut
from app.services.store import STORE

router = APIRouter()


@router.get("", response_model=list[PostingOut])
async def list_postings(limit: int = Query(default=20, ge=1, le=100), offset: int = Query(default=0, ge=0)) -> list[PostingOut]:
    rows = STORE.postings[offset : offset + limit]
    return [PostingOut(**row) for row in rows]
