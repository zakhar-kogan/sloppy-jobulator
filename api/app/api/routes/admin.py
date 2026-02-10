from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.security import get_human_principal
from app.schemas.admin import (
    ModuleTrustLevel,
    SourceTrustPolicyEnabledPatchRequest,
    SourceTrustPolicyOut,
    SourceTrustPolicyUpsertRequest,
)
from app.services.repository import (
    RepositoryNotFoundError,
    RepositoryUnavailableError,
    RepositoryValidationError,
    get_repository,
)

router = APIRouter()


@router.get("/source-trust-policy", response_model=list[SourceTrustPolicyOut])
async def list_source_trust_policy(
    principal=Depends(get_human_principal),
    repository=Depends(get_repository),
    source_key: str | None = Query(default=None, min_length=1),
    enabled: bool | None = Query(default=None),
    trust_level: ModuleTrustLevel | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[SourceTrustPolicyOut]:
    try:
        principal.require_scopes({"admin:write"})
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    try:
        rows = await repository.list_source_trust_policies(
            source_key=source_key,
            enabled=enabled,
            trust_level=trust_level,
            limit=limit,
            offset=offset,
        )
    except RepositoryValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except RepositoryUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return [SourceTrustPolicyOut(**row) for row in rows]


@router.put("/source-trust-policy/{source_key}", response_model=SourceTrustPolicyOut)
async def put_source_trust_policy(
    source_key: str,
    payload: SourceTrustPolicyUpsertRequest,
    principal=Depends(get_human_principal),
    repository=Depends(get_repository),
) -> SourceTrustPolicyOut:
    try:
        principal.require_scopes({"admin:write"})
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    if not principal.actor_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid human principal")

    try:
        await repository.upsert_source_trust_policy(
            source_key=source_key,
            trust_level=payload.trust_level,
            auto_publish=payload.auto_publish,
            requires_moderation=payload.requires_moderation,
            rules_json=payload.rules_json,
            enabled=payload.enabled,
            actor_user_id=principal.actor_id,
        )
        row = await repository.get_source_trust_policy(source_key=source_key)
    except RepositoryValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except RepositoryUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except RepositoryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return SourceTrustPolicyOut(**row)


@router.patch("/source-trust-policy/{source_key}", response_model=SourceTrustPolicyOut)
async def patch_source_trust_policy_enabled(
    source_key: str,
    payload: SourceTrustPolicyEnabledPatchRequest,
    principal=Depends(get_human_principal),
    repository=Depends(get_repository),
) -> SourceTrustPolicyOut:
    try:
        principal.require_scopes({"admin:write"})
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    if not principal.actor_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid human principal")

    try:
        row = await repository.set_source_trust_policy_enabled(
            source_key=source_key,
            enabled=payload.enabled,
            actor_user_id=principal.actor_id,
        )
    except RepositoryValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except RepositoryUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except RepositoryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return SourceTrustPolicyOut(**row)
