#!/usr/bin/env bash
# Automates docs/development_setup.rst (non-interactively, via `devbox run`).
#
# Usage:  scripts/dev_setup.sh [python_version]   (default 3.13)
#
# Assumes nix + devbox installed. Where config/secrets.json is not available
# (it normally comes from the production server via `fab initial-dev-setup`),
# a dummy one is generated.
set -euo pipefail
cd "$(dirname "$0")/.."
PYVER="${1:-3.13}"

dbx() { devbox run -- "$@"; }

dbx uv python install "$PYVER"
if [ ! -d .venv ]; then
    dbx uv venv --python "python$PYVER" --prompt cciw
fi
pwd > ".venv/lib/python$PYVER/site-packages/projectsource.pth"
dbx uv sync

# Equivalent of `fab initial-dev-setup`, minus fetching secrets from the server
[ -f cciw/settings_local.py ] || cp cciw/settings_local_example.py cciw/settings_local.py
mkdir -p ../secure_downloads_src ../logs
[ -f config/secrets.json ] || python3 scripts/create_dummy_secrets.py

grep -q "cciw.local" /etc/hosts || echo "127.0.0.1          cciw.local" | sudo tee -a /etc/hosts

# Postgres
if [ ! -f .devbox/virtenv/postgresql/data/PG_VERSION ]; then
    dbx initdb
fi
scripts/services.sh start
dbx bash -c 'dropdb --if-exists cciw_dev; createdb cciw_dev; psql -d template1 < ./scripts/setup_postgres_dev_db.sql'
dbx .venv/bin/python manage.py migrate
dbx .venv/bin/python manage.py loaddata fixtures/dev_db.json
echo "Done. Run: devbox run -- .venv/bin/python manage.py runserver 0.0.0.0:8000"
