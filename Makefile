SHELL := /bin/bash

DB_URL ?= postgresql://postgres:postgres@localhost:5432/sloppy_jobulator

.PHONY: build test lint typecheck dev dev-up db-up db-down db-reset test-integration mvp-smoke

build:
	python -m compileall api/app workers/app
	fnm exec --using 24.13.0 pnpm --dir web build

test:
	pytest api/tests
	pytest workers/tests

test-integration:
	SJ_DATABASE_URL=$(DB_URL) DATABASE_URL=$(DB_URL) pytest api/tests/test_discovery_jobs_integration.py

lint:
	ruff check api
	ruff check workers
	fnm exec --using 24.13.0 pnpm --dir web lint

typecheck:
	mypy api/app
	mypy workers/app
	fnm exec --using 24.13.0 pnpm --dir web typecheck

dev:
	@echo "Run services separately:"
	@echo "- API: uvicorn app.main:app --reload (from api/)"
	@echo "- Worker: python -m app.main (from workers/)"
	@echo "- Web: fnm use 24.13.0 && pnpm --dir web dev"

dev-up:
	@bash -lc 'set -euo pipefail; \
		make db-up; \
		make db-reset; \
		trap "kill 0" EXIT INT TERM; \
		UV_CACHE_DIR=/tmp/uv-cache SJ_DATABASE_URL=$(DB_URL) SJ_SUPABASE_URL=http://127.0.0.1:54321 SJ_SUPABASE_ANON_KEY=test-key uv run --project api --extra dev uvicorn app.main:app --host 127.0.0.1 --port 8000 & \
		UV_CACHE_DIR=/tmp/uv-cache SJ_WORKER_API_BASE_URL=http://127.0.0.1:8000 SJ_WORKER_API_KEY=local-processor-key uv run --project workers --extra dev python -m app.main & \
		SJ_API_URL=http://127.0.0.1:8000 SJ_ADMIN_BEARER=admin-token fnm exec --using 24.13.0 pnpm --dir web dev --hostname 127.0.0.1 --port 3000 & \
		wait'

db-up:
	docker compose up -d postgres

db-down:
	docker compose down

db-reset:
	DATABASE_URL=$(DB_URL) bash scripts/reset_db.sh

mvp-smoke:
	bash scripts/mvp-smoke.sh
