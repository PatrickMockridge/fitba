.PHONY: sync test lint format typecheck check check-all web-contract-check fixtures-check xg-check consistency-check data-coverage-check docs-check corrections-check metrics-check publication-check names-check transfers-check former-players-check former-players-refresh history-check matchday-check themes-check provenance-check availability-check needs-check league-migration-probe history-backfill history-backfill-transfers rumours-check squad-check scouting-check scouting-pages-check roles-check shapes-check career-roles-check player-page-check career-backfill career-refresh player-attributes-check probe ingest fixtures news forum cups transfers squad availability build validate publish web api-test sportmonks-attributes-test

BASE_PATH ?=

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

check: lint typecheck test docs-check corrections-check metrics-check consistency-check publication-check names-check transfers-check former-players-check history-check matchday-check themes-check analysis-check xg-check provenance-check availability-check needs-check rumours-check squad-check scouting-check roles-check shapes-check career-roles-check player-page-check player-attributes-check

check-all: check web-contract-check

web-contract-check:
	cd web && NEXT_PUBLIC_BASE_PATH="$(BASE_PATH)" npm run build
	uv run python scripts/check_web_contract.py --ci --base-path "$(BASE_PATH)"
	uv run python scripts/check_fixture_pages.py --base-path "$(BASE_PATH)"
	uv run python scripts/check_scouting.py --pages
	uv run python scripts/check_player_page.py --pages
	uv run python scripts/check_seo.py
	uv run python scripts/check_accessibility.py

fixtures-check:
	uv run python scripts/check_fixture_pages.py --base-path "$(BASE_PATH)"

xg-check:
	uv run python scripts/check_xg.py

consistency-check:
	uv run python scripts/check_consistency.py

data-coverage-check:
	uv run python scripts/check_data_coverage.py

docs-check:
	uv run python scripts/check_docs.py

corrections-check:
	uv run python scripts/check_corrections.py

metrics-check:
	uv run python scripts/check_metrics.py --strict

publication-check:
	uv run python scripts/check_publication.py

names-check:
	uv run python scripts/check_names.py

transfers-check:
	uv run python scripts/check_transfers.py

former-players-check:
	uv run python scripts/check_former_players.py

former-players-refresh:
	uv run fitba former-players refresh --max-requests 180

history-check:
	uv run python scripts/check_history.py

matchday-check:
	uv run python scripts/check_matchday.py

themes-check:
	uv run python scripts/check_themes.py

analysis-check:
	uv run python scripts/check_analysis.py

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

scouting-check:
	uv run python scripts/check_scouting.py

scouting-pages-check:
	uv run python scripts/check_scouting.py --pages

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
	uv run fitba publish --season current --profile public --require-validation

web:
	cd web && npm run dev
