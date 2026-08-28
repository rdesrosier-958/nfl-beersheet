#!/usr/bin/env bash
# Rebuild and publish every league profile under config/leagues/.
set -euo pipefail
cd "$(dirname "$0")/.."

for profile in config/leagues/*.yaml; do
  league="$(basename "$profile" .yaml)"
  echo "=== ${league} ==="
  ./scripts/refresh.sh --league "$league" "$@"
done
