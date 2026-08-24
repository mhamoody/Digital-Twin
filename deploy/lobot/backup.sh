#!/usr/bin/env bash
# Back up the configured pilot database and retain the newest seven copies.
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${project_root}"
env_file="${DIGITAL_TWIN_ENV_FILE:-${project_root}/.env.lobot}"
set -a
# shellcheck disable=SC1090
source "${env_file}"
set +a
: "${DIGITAL_TWIN_DATABASE_URL:?DIGITAL_TWIN_DATABASE_URL is required}"
mkdir -p var/backups
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
if [[ "${DIGITAL_TWIN_DATABASE_URL}" == sqlite* ]]; then
  backup_file="var/backups/digital_twin_${timestamp}.sqlite3"
  python - "${backup_file}" <<'PY'
import os
import sqlite3
import sys
from pathlib import Path

from sqlalchemy.engine import make_url

source = Path(make_url(os.environ["DIGITAL_TWIN_DATABASE_URL"]).database)
if not source.is_absolute():
    source = (Path.cwd() / source).resolve()
if not source.is_file():
    raise SystemExit(f"SQLite database not found: {source}")
target = Path(sys.argv[1]).resolve()
with sqlite3.connect(source) as source_connection, sqlite3.connect(target) as target_connection:
    source_connection.backup(target_connection)
PY
else
  command -v pg_dump >/dev/null 2>&1 || {
    echo "pg_dump is required for PostgreSQL backups." >&2
    exit 1
  }
  backup_file="var/backups/digital_twin_${timestamp}.dump"
  postgres_url="${DIGITAL_TWIN_DATABASE_URL/postgresql+psycopg/postgresql}"
  pg_dump --format=custom --file="${backup_file}" "${postgres_url}"
fi
chmod 600 "${backup_file}" 2>/dev/null || true
mapfile -t old_backups < <(find var/backups -maxdepth 1 -type f \( -name 'digital_twin_*.dump' -o -name 'digital_twin_*.sqlite3' \) -printf '%T@ %p\n' | sort -rn | tail -n +8 | cut -d' ' -f2-)
if ((${#old_backups[@]})); then
  rm -- "${old_backups[@]}"
fi
echo "Backup created: ${backup_file}"
