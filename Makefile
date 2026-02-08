SHELL := /bin/bash

.PHONY: build test lint typecheck dev

build:
	python -m compileall api/app workers/app
	fnm exec --using 24.13.0 pnpm --dir web build

test:
	pytest api/tests
	pytest workers/tests

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
