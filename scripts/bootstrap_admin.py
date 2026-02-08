#!/usr/bin/env python3
"""Bootstrap helper for creating initial admin metadata.

This script currently emits SQL templates. In the next phase it should call
Supabase admin APIs or run parameterized SQL against the target environment.
"""

from __future__ import annotations

import argparse


def render_sql(email: str) -> str:
    return f"""-- Manual bootstrap SQL
-- Replace USER_UUID with the auth.users id for {email}
-- and connect role mapping when auth tables are finalized.

insert into provenance_events (entity_type, event_type, actor_type, payload)
values (
  'bootstrap',
  'admin_seed_requested',
  'system',
  '{{"email": "{email}"}}'::jsonb
);
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Emit bootstrap SQL for initial admin setup.")
    parser.add_argument("--email", required=True, help="Admin user email")
    args = parser.parse_args()

    print(render_sql(args.email))


if __name__ == "__main__":
    main()
