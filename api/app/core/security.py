import hashlib
import hmac
from typing import Any

import httpx
from fastapi import Depends, Header, HTTPException, status

from app.core.auth import Principal, PrincipalType
from app.core.config import Settings, get_settings
from app.services.repository import RepositoryUnavailableError, get_repository

ROLE_SCOPES: dict[str, set[str]] = {
    "user": {"catalog:read", "submission:write"},
    "moderator": {"catalog:read", "submission:write", "moderation:read", "moderation:write"},
    "admin": {"catalog:read", "submission:write", "moderation:read", "moderation:write", "admin:write"},
}


async def get_machine_principal(
    settings: Settings = Depends(get_settings),
    repository=Depends(get_repository),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    x_module_id: str | None = Header(default=None, alias="X-Module-Id"),
) -> Principal:
    if not x_api_key or not x_module_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"machine auth requires {settings.api_key_header} and X-Module-Id",
        )

    try:
        credentials = await repository.get_machine_credentials(x_module_id)
    except RepositoryUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid module credentials")

    key_hash = hashlib.sha256(x_api_key.encode("utf-8")).hexdigest()
    matched = next((record for record in credentials if hmac.compare_digest(record.key_hash, key_hash)), None)
    if not matched:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid module credentials")

    return Principal(
        principal_type=PrincipalType.MACHINE,
        subject=matched.module_id,
        scopes=set(matched.scopes),
        actor_id=matched.module_db_id,
    )


async def get_human_principal(
    settings: Settings = Depends(get_settings),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> Principal:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="human auth requires bearer token",
        )

    token = authorization.split(" ", maxsplit=1)[1].strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="empty bearer token")

    if not settings.supabase_url or not settings.supabase_anon_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase auth is not configured",
        )

    user = await _fetch_supabase_user(
        supabase_url=settings.supabase_url,
        supabase_anon_key=settings.supabase_anon_key,
        token=token,
        timeout_seconds=settings.auth_timeout_seconds,
    )
    user_id = user.get("id")
    if not isinstance(user_id, str) or not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid bearer token")

    role = _resolve_human_role(user)

    return Principal(
        principal_type=PrincipalType.HUMAN,
        subject=user_id,
        role=role,
        scopes=ROLE_SCOPES.get(role, ROLE_SCOPES["user"]),
        actor_id=user_id,
    )


async def _fetch_supabase_user(
    *,
    supabase_url: str,
    supabase_anon_key: str,
    token: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {token}",
        "apikey": supabase_anon_key,
    }
    url = f"{supabase_url.rstrip('/')}/auth/v1/user"

    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.get(url, headers=headers)
    except httpx.HTTPError as exc:  # pragma: no cover - network dependent
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase auth verification unavailable",
        ) from exc

    if response.status_code in {401, 403}:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid bearer token")
    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase auth verification failed",
        )

    return response.json()


def _resolve_human_role(user: dict[str, Any]) -> str:
    app_metadata = user.get("app_metadata")
    if isinstance(app_metadata, dict):
        role = app_metadata.get("role")
        if isinstance(role, str) and role:
            return role

    user_metadata = user.get("user_metadata")
    if isinstance(user_metadata, dict):
        role = user_metadata.get("role")
        if isinstance(role, str) and role:
            return role

    return "user"
