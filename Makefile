SHELL := /bin/bash

DB_URL ?= postgresql://postgres:postgres@localhost:5432/sloppy_jobulator

.PHONY: build test lint typecheck dev db-up db-down db-reset test-integration

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

db-up:
	docker compose up -d postgres

db-down:
	docker compose down

db-reset:
	DATABASE_URL=$(DB_URL) bash scripts/reset_db.sh
