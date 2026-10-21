.PHONY: sync test lint format typecheck check probe ingest build validate publish web

sync:
	uv sync

test:
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

typecheck:
	uv run pyright

check: lint typecheck test

probe:
	uv run python scripts/probe_source.py

ingest:
	uv run fitba ingest --season current

build:
	uv run fitba build --season all

validate:
	uv run fitba validate --season current

publish:
	uv run fitba publish --season current

web:
	cd web && npm run dev
