#!/usr/bin/env bash
# Daily data refresh: fetch sources, rescore, publish sheet.
# For injury/news nudges, run the full skill pass (see .cursor/skills/update-nfl-beersheet/SKILL.md).
set -euo pipefail
cd "$(dirname "$0")/.."

LOG_DIR="logs"
mkdir -p "$LOG_DIR"
STAMP="$(date +%Y-%m-%d)"
LOG="$LOG_DIR/daily-${STAMP}.log"

{
  echo "=== nfl-beersheet daily refresh $(date -Iseconds) ==="
  ./scripts/refresh.sh
  echo "=== done ==="
} 2>&1 | tee -a "$LOG"
