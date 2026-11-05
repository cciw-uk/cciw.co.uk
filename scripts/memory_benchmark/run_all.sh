#!/usr/bin/env bash
# Run the memory benchmark for each environment in turn (plus a 3.14 run with
# the multiprocessing start method forced back to "fork"), then summarise.
# Usage: scripts/memory_benchmark/run_all.sh [duration_seconds]
set -euo pipefail
cd "$(dirname "$0")/../.."
DUR="${1:-300}"
B=../cciw-bench
PY=.venv/bin/python
R=scripts/memory_benchmark/run_benchmark.py
OUT=scripts/memory_benchmark/results/run-$(date +%Y%m%d-%H%M%S)
mkdir -p "$OUT"
for v in 3.13.13 3.13.18 3.14.4 3.14.10; do
    $PY $R $B/py$v --duration "$DUR" --out "$OUT/py$v.json" | tail -n +3 >> "$OUT/log.txt"
done
$PY $R $B/py3.14.10 --duration "$DUR" --label py3.14.10-fork \
    --extra-env PYTHONPATH="$PWD/scripts/memory_benchmark/force_fork" --out "$OUT/py3.14.10-fork.json" | tail -n +3 >> "$OUT/log.txt"
$PY scripts/memory_benchmark/summarise.py "$OUT"/*.json | tee "$OUT/summary.txt"
