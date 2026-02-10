#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def _user_payload_for_token(token: str) -> dict[str, object] | None:
    if token == "admin-token":
        return {
            "id": "11111111-1111-1111-1111-111111111111",
            "app_metadata": {"role": "admin"},
            "user_metadata": {},
        }
    if token == "moderator-token":
        return {
            "id": "22222222-2222-2222-2222-222222222222",
            "app_metadata": {"role": "moderator"},
            "user_metadata": {},
        }
    if token == "user-token":
        return {
            "id": "33333333-3333-3333-3333-333333333333",
            "app_metadata": {"role": "user"},
            "user_metadata": {},
        }
    return None


class MockSupabaseHandler(BaseHTTPRequestHandler):
    server_version = "MockSupabase/1.0"

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler signature
        if self.path == "/healthz":
            self._write_json(HTTPStatus.OK, {"status": "ok"})
            return

        if self.path != "/auth/v1/user":
            self._write_json(HTTPStatus.NOT_FOUND, {"detail": "not found"})
            return

        authorization = self.headers.get("Authorization", "")
        if not authorization.lower().startswith("bearer "):
            self._write_json(HTTPStatus.UNAUTHORIZED, {"detail": "missing bearer token"})
            return

        token = authorization.split(" ", maxsplit=1)[1].strip()
        user = _user_payload_for_token(token)
        if user is None:
            self._write_json(HTTPStatus.UNAUTHORIZED, {"detail": "invalid token"})
            return

        self._write_json(HTTPStatus.OK, user)

    def log_message(self, _: str, *args: object) -> None:
        # Keep logs terse for test runs.
        if args:
            print("mock-supabase:", *args)

    def _write_json(self, status: HTTPStatus, payload: dict[str, object]) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def main() -> None:
    parser = argparse.ArgumentParser(description="Mock Supabase auth /auth/v1/user endpoint.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), MockSupabaseHandler)
    print(f"mock-supabase listening on http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
