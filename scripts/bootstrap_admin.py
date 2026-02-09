#!/usr/bin/env python3
"""Emit deterministic SQL for Supabase human-role bootstrap."""

from __future__ import annotations

import argparse


def _quote_sql(value: str) -> str:
    escaped = value.replace("'", "''")
    return f"'{escaped}'"


def render_sql(*, role: str, user_id: str | None, email: str | None, actor: str) -> str:
    role_value = _quote_sql(role)
    actor_value = _quote_sql(actor)

    if user_id:
        target_where = f"id = {_quote_sql(user_id)}::uuid"
        target_payload = f"jsonb_build_object('user_id', {_quote_sql(user_id)}, 'role', {role_value})"
    else:
        assert email is not None
        target_where = f"email = {_quote_sql(email)}"
        target_payload = f"jsonb_build_object('email', {_quote_sql(email)}, 'role', {role_value})"

    return f"""-- Supabase human role bootstrap SQL
-- Run this in the Supabase SQL editor (or equivalent privileged Postgres session).

update auth.users
set raw_app_meta_data = coalesce(raw_app_meta_data, '{{}}'::jsonb) || jsonb_build_object('role', {role_value})
where {target_where};

insert into provenance_events (entity_type, event_type, actor_type, payload)
values ('bootstrap', 'human_role_bootstrap', {actor_value}, {target_payload});
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Emit SQL to bootstrap a Supabase human role.")
    parser.add_argument(
        "--role",
        choices=["user", "moderator", "admin"],
        default="admin",
        help="Role to assign in auth.users.raw_app_meta_data.role",
    )
    identity_group = parser.add_mutually_exclusive_group(required=True)
    identity_group.add_argument("--user-id", help="Supabase auth.users id (UUID)")
    identity_group.add_argument("--email", help="Supabase auth.users email")
    parser.add_argument(
        "--actor",
        default="system",
        help="Actor label for provenance event payload",
    )
    args = parser.parse_args()

    print(
        render_sql(
            role=args.role,
            user_id=args.user_id,
            email=args.email,
            actor=args.actor,
        )
    )


if __name__ == "__main__":
    main()
