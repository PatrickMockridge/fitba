#!/usr/bin/env bash
# Local data cadence. Run on main only; uses the gitignored .env key.
#
#   scripts/local_update.sh daily     # full update
#   scripts/local_update.sh matchday  # update only when a fixture is due
#
# Installed as two cron entries by scripts/install_local_cadence.sh.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:-matchday}"
STATE_DIR="${HOME}/.local/state/fitba"

export PATH="/home/patrick/miniforge3/bin:/usr/local/bin:/usr/bin:/bin"
export GIT_TERMINAL_PROMPT=0
export GIT_SSH_COMMAND="ssh -o BatchMode=yes"
mkdir -p "$STATE_DIR"

exec 9>"${STATE_DIR}/update.lock"
if ! flock -n 9; then
  echo "$(date -Is) another fitba update is running; skipping"
  exit 0
fi

cd "$ROOT"
echo "$(date -Is) local update mode=${MODE}"

if [ "$(git branch --show-current)" != "main" ]; then
  echo "not on main; skipping (current: $(git branch --show-current))"
  exit 0
fi

case "$MODE" in
  daily)
    ;;
  matchday)
    due_output="$(uv run python "$ROOT/scripts/matchday_refresh_due.py")"
    echo "$due_output"
    echo "$due_output" | grep -q "due: true" || { echo "no post-match update due"; exit 0; }
    ;;
  *)
    echo "usage: $0 [daily|matchday]" >&2
    exit 2
    ;;
esac

uv run fitba update --mode "$MODE" --force-results --json >> "$STATE_DIR/update.jsonl"


if [ -z "$(git status --porcelain web/data/generated)" ]; then
  echo "no data changes"
  exit 0
fi

git add web/data/generated
git -c user.name="fitba-bot" -c user.email="fitba-bot@users.noreply.github.com" \
  commit -m "data: local update $(date -u +%F)" \
  -m "Co-Authored-By: Claude Code <noreply@anthropic.com>"

pushed=0
for attempt in 1 2 3; do
  if git pull --rebase --autostash && git push; then
    pushed=1
    break
  fi
  sleep $((attempt * 5))
done
if [ "$pushed" != "1" ]; then
  echo "data commit created but push failed; resolve manually" >&2
  exit 1
fi
echo "$(date -Is) local update complete"
