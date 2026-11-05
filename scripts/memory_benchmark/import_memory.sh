#!/usr/bin/env bash
# Usage: scripts/memory_benchmark/import_memory.sh ../cciw-bench/py3.14 [--tracemalloc]
# Runs import_memory.py in the given benchmark env, with production settings.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ENV_DIR="$(cd "$1" && pwd)"; shift
cd "$ENV_DIR/home"
HOME="$ENV_DIR/home" unshare --user --map-root-user --uts sh -c \
  'hostname cciw-bench && exec "$@"' sh "$ENV_DIR/src/.venv/bin/python" -W ignore "$HERE/import_memory.py" "$@" 2>&1 \
  | grep -v "weasyprint.progress"
