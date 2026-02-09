from __future__ import annotations

import subprocess
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "bootstrap_admin.py"


def _run_script(*args: str) -> str:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def test_bootstrap_script_emits_sql_for_user_id_target() -> None:
    user_id = "00000000-0000-0000-0000-000000000123"
    output = _run_script("--user-id", user_id, "--role", "moderator", "--actor", "cli")

    assert "update auth.users" in output
    assert f"where id = '{user_id}'::uuid;" in output
    assert "jsonb_build_object('role', 'moderator')" in output
    assert "values ('bootstrap', 'human_role_bootstrap', 'cli'" in output


def test_bootstrap_script_emits_sql_for_email_target() -> None:
    output = _run_script("--email", "admin@example.edu", "--role", "admin")

    assert "where email = 'admin@example.edu';" in output
    assert "jsonb_build_object('email', 'admin@example.edu', 'role', 'admin')" in output
