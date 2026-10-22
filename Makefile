.PHONY: sync test lint format typecheck check docs-check names-check transfers-check history-check matchday-check themes-check provenance-check availability-check needs-check league-migration-probe history-backfill history-backfill-transfers rumours-check squad-check roles-check shapes-check career-roles-check player-page-check career-backfill career-refresh player-attributes-check probe ingest fixtures news forum cups transfers squad availability build validate publish web api-test sportmonks-attributes-test

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

check: lint typecheck test docs-check names-check transfers-check history-check matchday-check themes-check provenance-check availability-check needs-check rumours-check squad-check roles-check shapes-check career-roles-check player-page-check player-attributes-check

docs-check:
	uv run python scripts/check_docs.py

names-check:
	uv run python scripts/check_names.py

transfers-check:
	uv run python scripts/check_transfers.py

history-check:
	uv run python scripts/check_history.py

matchday-check:
	uv run python scripts/check_matchday.py

themes-check:
	uv run python scripts/check_themes.py

provenance-check:
	uv run python scripts/check_provenance.py

availability-check:
	uv run python scripts/check_availability.py

needs-check:
	uv run python scripts/check_needs.py

league-migration-probe:
	uv run python scripts/probe_league_migration.py --season current

availability:
	uv run fitba availability --refresh

history-backfill:
	uv run fitba history --backfill --max-requests 200

history-backfill-transfers:
	uv run fitba history --backfill-transfers

rumours-check:
	uv run python scripts/check_rumours.py

squad-check:
	uv run python scripts/check_squad.py

roles-check:
	uv run python scripts/check_roles.py

shapes-check:
	uv run python scripts/check_shapes.py

career-roles-check:
	uv run python scripts/check_career_roles.py

player-page-check:
	uv run python scripts/check_player_page.py

career-backfill:
	uv run fitba career backfill --max-requests 1500

career-refresh:
	uv run fitba career refresh

player-attributes-check:
	uv run python scripts/check_player_attributes.py

sportmonks-attributes-test:
	uv run python scripts/probe_sportmonks_attributes.py

api-test:
	uv run python scripts/probe_api_football.py

probe:
	uv run python scripts/probe_source.py

ingest:
	uv run fitba ingest --season current
	uv run fitba cups
	uv run fitba fixtures --club aberdeen
	uv run fitba transfers
	uv run fitba squad
	uv run fitba news
	uv run fitba forum

cups:
	uv run fitba cups

transfers:
	uv run fitba transfers

fixtures:
	uv run fitba fixtures --club aberdeen

squad:
	uv run fitba squad

news:
	uv run fitba news

forum:
	uv run fitba forum

build:
	uv run fitba build --season all

validate:
	uv run fitba validate --season current

publish:
	uv run fitba publish --season current

web:
	cd web && npm run dev
