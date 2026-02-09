from fastapi import APIRouter

from app.api.routes import candidates, discoveries, evidence, health, jobs, postings

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(postings.router, prefix="/postings", tags=["public"])
api_router.include_router(discoveries.router, prefix="/discoveries", tags=["connector"])
api_router.include_router(evidence.router, prefix="/evidence", tags=["connector"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["processor"])
api_router.include_router(candidates.router, prefix="/candidates", tags=["moderation"])
