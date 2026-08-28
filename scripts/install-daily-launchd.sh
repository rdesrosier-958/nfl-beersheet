#!/usr/bin/env bash
# Install macOS launchd job: daily refresh at 8:00 AM local time.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PLIST_SRC="$ROOT/scripts/com.nfl-beersheet.daily.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.nfl-beersheet.daily.plist"

chmod +x "$ROOT/scripts/daily_refresh.sh" "$ROOT/scripts/refresh.sh"
mkdir -p "$ROOT/logs"
cp "$PLIST_SRC" "$PLIST_DST"
launchctl bootout "gui/$(id -u)/com.nfl-beersheet.daily" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_DST"
launchctl enable "gui/$(id -u)/com.nfl-beersheet.daily"
echo "Installed daily refresh at 8:00 AM → $PLIST_DST"
echo "Logs: $ROOT/logs/"
echo ""
echo "Uninstall: launchctl bootout gui/$(id -u)/com.nfl-beersheet.daily && rm $PLIST_DST"
