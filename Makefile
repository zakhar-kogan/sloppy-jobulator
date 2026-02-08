SHELL := /bin/bash

.PHONY: build test lint typecheck dev

build:
	@echo "Build targets are language-specific during bootstrap."
	@echo "- API: python -m compileall api/app"
	@echo "- Workers: python -m compileall workers/app"
	@echo "- Web: npm run build --prefix web"

test:
	@echo "API tests: pytest api/tests"
	@echo "Worker tests: pytest workers/tests"

lint:
	@echo "API lint: ruff check api"
	@echo "Workers lint: ruff check workers"
	@echo "Web lint: npm run lint --prefix web"

typecheck:
	@echo "API typecheck: mypy api/app"
	@echo "Workers typecheck: mypy workers/app"
	@echo "Web typecheck: npm run typecheck --prefix web"

dev:
	@echo "Run services separately:"
	@echo "- API: uvicorn app.main:app --reload (from api/)"
	@echo "- Worker: python -m app.main (from workers/)"
	@echo "- Web: npm run dev --prefix web"
