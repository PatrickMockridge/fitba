#!/usr/bin/env bash
# Install the local fitba data cadence as two cron entries.
#
# The jobs use the gitignored .env key and only update when the checkout is on
# main. Logs go to ~/.local/state/fitba/update.log.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="${HOME}/.local/state/fitba"
LOG="${STATE_DIR}/update.log"

mkdir -p "$STATE_DIR"

current="$(crontab -l 2>/dev/null || true)"
if printf '%s\n' "$current" | grep -q "# fitba data cadence"; then
  echo "fitba cadence already installed"
  exit 0
fi

tmp="$(mktemp)"
printf '%s\n' "$current" > "$tmp"
cat >> "$tmp" <<EOF

# fitba data cadence
17 6 * * * cd $ROOT && $ROOT/scripts/local_update.sh daily >> $LOG 2>&1
0 */2 * * * cd $ROOT && $ROOT/scripts/local_update.sh matchday >> $LOG 2>&1
EOF
crontab "$tmp"
rm -f "$tmp"
echo "installed fitba cadence:"
crontab -l | tail -4
