#!/usr/bin/env bash
# Restore one project database into a newly created, empty target database.
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: bash deploy/lobot/restore.sh PATH_TO_DUMP" >&2
  exit 2
fi
dump_file="$1"
if [[ ! -f "${dump_file}" ]]; then
  echo "Dump file not found: ${dump_file}" >&2
  exit 1
fi

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${project_root}"
env_file="${DIGITAL_TWIN_ENV_FILE:-${project_root}/.env.lobot}"
set -a
# shellcheck disable=SC1090
source "${env_file}"
set +a
: "${DIGITAL_TWIN_DATABASE_URL:?DIGITAL_TWIN_DATABASE_URL is required}"
echo "This command expects a newly created empty target database."
read -r -p "Type RESTORE to continue: " confirmation
if [[ "${confirmation}" != "RESTORE" ]]; then
  echo "Restore cancelled."
  exit 1
fi
if [[ "${DIGITAL_TWIN_DATABASE_URL}" == sqlite* ]]; then
  python - "${dump_file}" <<'PY'
import os
import hashlib
import sqlite3
import sys
from pathlib import Path

from sqlalchemy.engine import make_url

source = Path(sys.argv[1]).resolve()
with source.open("rb") as handle:
    header = handle.read(16)
if header != b"SQLite format 3\x00":
    raise SystemExit("The supplied file is not a SQLite database.")
digest = hashlib.sha256()
with source.open("rb") as handle:
    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
        digest.update(chunk)
print(f"Source bytes: {source.stat().st_size}")
print(f"Source SHA-256: {digest.hexdigest()}")
target = Path(make_url(os.environ["DIGITAL_TWIN_DATABASE_URL"]).database)
if not target.is_absolute():
    target = (Path.cwd() / target).resolve()
if target.exists():
    raise SystemExit(f"Target already exists; it was not overwritten: {target}")
target.parent.mkdir(parents=True, exist_ok=True)
temporary = target.with_suffix(target.suffix + ".restore-tmp")
if temporary.exists():
    raise SystemExit(f"A previous temporary restore exists; remove it first: {temporary}")
try:
    source_uri = f"file:{source.as_posix()}?mode=ro"
    with sqlite3.connect(source_uri, uri=True) as source_connection:
        source_check = source_connection.execute("PRAGMA quick_check").fetchone()
        if source_check != ("ok",):
            raise sqlite3.DatabaseError(f"source integrity check failed: {source_check}")
        with sqlite3.connect(temporary) as target_connection:
            source_connection.backup(target_connection)
            target_check = target_connection.execute("PRAGMA quick_check").fetchone()
            if target_check != ("ok",):
                raise sqlite3.DatabaseError(f"restored integrity check failed: {target_check}")
    temporary.replace(target)
except Exception:
    temporary.unlink(missing_ok=True)
    raise
print(f"SQLite database restored to {target}")
PY
else
  command -v pg_restore >/dev/null 2>&1 || {
    echo "pg_restore is required for a PostgreSQL restore." >&2
    exit 1
  }
  postgres_url="${DIGITAL_TWIN_DATABASE_URL/postgresql+psycopg/postgresql}"
  pg_restore --exit-on-error --no-owner --no-privileges \
    --dbname="${postgres_url}" "${dump_file}"
fi
echo "Restore completed. Run bash deploy/lobot/start.sh."
