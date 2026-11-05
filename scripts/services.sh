#!/usr/bin/env bash
# Start/stop devbox services (postgres) in the background.
# Usage: scripts/services.sh start|stop
set -euo pipefail
cd "$(dirname "$0")/.."
case "${1:-start}" in
  start)
    if devbox run -- pg_isready -h localhost -q 2>/dev/null; then echo "postgres already running"; exit 0; fi
    devbox services up -b
    for _ in $(seq 30); do devbox run -- pg_isready -h localhost -q && break; sleep 1; done ;;
  stop) devbox services stop ;;
esac
