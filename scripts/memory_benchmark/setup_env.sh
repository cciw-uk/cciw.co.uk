#!/usr/bin/env bash
# Create an isolated copy of the project (git worktree) with a venv for a
# given Python version, for memory benchmarking.
#
# Usage: scripts/memory_benchmark/setup_env.sh 3.14 [git-ref]
#        UV=~/.local/uv-latest/uv scripts/memory_benchmark/setup_env.sh 3.14.10
#
# Creates ../cciw-bench/py<VERSION>/src (worktree) with .venv inside, and
# ../cciw-bench/py<VERSION>/home (fake $HOME, like production's /home/cciw).
# For versions other than 3.13, pyproject.toml `requires-python` is changed and
# `uv lock` re-run, mimicking what was done for the production upgrade.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
PYVER="$1"
REF="${2:-HEAD}"
BENCH_ROOT="${BENCH_ROOT:-$(dirname "$REPO")/cciw-bench}"
DIR="$BENCH_ROOT/py$PYVER"
SRC="$DIR/src"
# Override with UV=/path/to/uv to use a newer uv that knows newer Python patch releases
UV="${UV:-$REPO/.devbox/nix/profile/default/bin/uv}"
[ -x "$UV" ] || UV=uv
MINOR="$(echo "$PYVER" | cut -d. -f1,2)"

mkdir -p "$DIR/home/logs"
if [ ! -d "$SRC" ]; then
    git -C "$REPO" worktree add --detach "$SRC" "$REF"
fi
cp "$REPO/config/secrets.json" "$SRC/config/secrets.json"
cp "$REPO/cciw/settings_local.py" "$SRC/cciw/settings_local.py"

cd "$SRC"
sed -i -E "s/^requires-python = .*/requires-python = \"==$MINOR.*\"/" pyproject.toml
"$UV" python install "$PYVER"
# NB: venvs created with a minor version (e.g. "3.14") are linked to uv's
# "minor version" directory and silently move to newer patch releases when
# they are installed. Give a full version (e.g. 3.14.4) to pin it.
if [ ! -d .venv ] || ! .venv/bin/python -c "import sys; v='$PYVER'.split('.'); sys.exit(list(map(int, v)) != list(sys.version_info[:len(v)]))"; then
    rm -rf .venv
    "$UV" venv --python "$PYVER" --prompt "cciw-$PYVER"
fi
# --upgrade-package psycopg2-binary works around uv choosing the sdist (no wheel for
# the new Python in the old lock) and failing to build. It does not change versions.
"$UV" lock --upgrade-package psycopg2-binary
"$UV" sync   # same as production (fabfile install_requirements)
PYMINOR=$(.venv/bin/python -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')
pwd > ".venv/lib/python$PYMINOR/site-packages/projectsource.pth"
# psutil is needed by the measurement script; it's a main dependency already.
.venv/bin/python -c 'import sys, django; print(sys.version, "Django", django.__version__)'
