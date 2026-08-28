#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements.txt

LEAGUE_ARGS=()
BUILD_ARGS=()
COMMAND=build

while [[ $# -gt 0 ]]; do
  case "$1" in
    --league)
      LEAGUE_ARGS=(--league "$2")
      shift 2
      ;;
    build|sheet|picks|init-sheet)
      COMMAND="$1"
      shift
      ;;
    *)
      BUILD_ARGS+=("$1")
      shift
      ;;
  esac
done

if [[ -n "${NFL_LEAGUE:-}" && ${#LEAGUE_ARGS[@]} -eq 0 ]]; then
  LEAGUE_ARGS=(--league "$NFL_LEAGUE")
fi

PYTHONPATH=src python -m nfl "${LEAGUE_ARGS[@]}" "$COMMAND" ${BUILD_ARGS[@]+"${BUILD_ARGS[@]}"}
