from fastapi import Depends, Header, HTTPException, status

from app.core.auth import Principal, PrincipalType, parse_scope_header
from app.core.config import Settings, get_settings


async def get_machine_principal(
    settings: Settings = Depends(get_settings),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    x_module_id: str | None = Header(default=None, alias="X-Module-Id"),
    x_module_scopes: str | None = Header(default=None, alias="X-Module-Scopes"),
) -> Principal:
    if not x_api_key or not x_module_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"machine auth requires {settings.api_key_header} and X-Module-Id",
        )

    scopes = parse_scope_header(x_module_scopes)
    return Principal(
        principal_type=PrincipalType.MACHINE,
        subject=x_module_id,
        scopes=scopes,
    )


async def get_human_principal(
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_user_role: str | None = Header(default=None, alias="X-User-Role"),
) -> Principal:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="human auth requires bearer token",
        )

    token = authorization.split(" ", maxsplit=1)[1].strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="empty bearer token")

    return Principal(
        principal_type=PrincipalType.HUMAN,
        subject="supabase-user",
        role=x_user_role or "user",
        scopes={"catalog:read", "submission:write"},
    )
