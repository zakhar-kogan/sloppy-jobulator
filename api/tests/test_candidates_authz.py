from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import pytest
from fastapi.testclient import TestClient

import app.core.security as security
from app.core.config import get_settings
from app.main import app
from app.services.repository import RepositoryNotFoundError, get_repository


class FakeModerationRepository:
    def __init__(self) -> None:
        now = datetime.now(timezone.utc)
        self._candidates: list[dict[str, Any]] = [
            {
                "id": "11111111-1111-1111-1111-111111111111",
                "state": "needs_review",
                "dedupe_confidence": 0.72,
                "risk_flags": ["needs_human_review"],
                "extracted_fields": {"title": "Example Role"},
                "discovery_ids": ["22222222-2222-2222-2222-222222222222"],
                "posting_id": None,
                "created_at": now,
                "updated_at": now,
            }
        ]

    async def list_candidates(self, limit: int, offset: int, state: str | None) -> list[dict[str, Any]]:
        rows = self._candidates
        if state:
            rows = [row for row in rows if row["state"] == state]
        return rows[offset : offset + limit]

    async def update_candidate_state(
        self,
        *,
        candidate_id: str,
        state: str,
        actor_user_id: str,
        reason: str | None,
    ) -> dict[str, Any]:
        for row in self._candidates:
            if row["id"] != candidate_id:
                continue
            row["state"] = state
            row["updated_at"] = datetime.now(timezone.utc)
            return row
        raise RepositoryNotFoundError("candidate not found")


@pytest.fixture
def authz_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    os.environ["SJ_SUPABASE_URL"] = "https://example.supabase.co"
    os.environ["SJ_SUPABASE_ANON_KEY"] = "anon-key"
    get_settings.cache_clear()

    fake_repo = FakeModerationRepository()
    app.dependency_overrides[get_repository] = lambda: fake_repo

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
    os.environ.pop("SJ_SUPABASE_URL", None)
    os.environ.pop("SJ_SUPABASE_ANON_KEY", None)
    get_settings.cache_clear()


def _mock_supabase_user(monkeypatch: pytest.MonkeyPatch, user: dict[str, Any]) -> None:
    async def _fake_fetch(**_: Any) -> dict[str, Any]:
        return user

    monkeypatch.setattr(security, "_fetch_supabase_user", _fake_fetch)


def test_candidates_list_denies_user_role(authz_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_supabase_user(
        monkeypatch,
        {"id": "user-1", "app_metadata": {"role": "user"}},
    )

    response = authz_client.get("/candidates", headers={"Authorization": "Bearer token"})
    assert response.status_code == 403


def test_candidates_list_allows_moderator(authz_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_supabase_user(
        monkeypatch,
        {"id": "moderator-1", "app_metadata": {"role": "moderator"}},
    )

    response = authz_client.get("/candidates", headers={"Authorization": "Bearer token"})
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["state"] == "needs_review"


def test_candidates_patch_denies_user_role(authz_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_supabase_user(
        monkeypatch,
        {"id": "user-1", "app_metadata": {"role": "user"}},
    )

    response = authz_client.patch(
        "/candidates/11111111-1111-1111-1111-111111111111",
        json={"state": "publishable"},
        headers={"Authorization": "Bearer token"},
    )
    assert response.status_code == 403


def test_candidates_patch_allows_admin(authz_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_supabase_user(
        monkeypatch,
        {"id": "admin-1", "app_metadata": {"role": "admin"}},
    )

    response = authz_client.patch(
        "/candidates/11111111-1111-1111-1111-111111111111",
        json={"state": "publishable", "reason": "reviewed"},
        headers={"Authorization": "Bearer token"},
    )
    assert response.status_code == 200
    assert response.json()["state"] == "publishable"


def test_role_resolution_uses_only_app_metadata_for_elevated_roles() -> None:
    role = security._resolve_human_role(
        {
            "id": "user-1",
            "app_metadata": {},
            "user_metadata": {"role": "moderator"},
        }
    )
    assert role == "user"


def test_role_resolution_supports_app_metadata_roles_array() -> None:
    role = security._resolve_human_role(
        {
            "id": "moderator-1",
            "app_metadata": {"roles": ["moderator", "user"]},
        }
    )
    assert role == "moderator"
