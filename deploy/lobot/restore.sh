#!/usr/bin/env bash
# Restore one project dump into a newly created, empty PostgreSQL database.
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
command -v pg_restore >/dev/null 2>&1 || {
  echo "pg_restore is required." >&2
  exit 1
}

echo "This command expects a newly created empty target database."
read -r -p "Type RESTORE to continue: " confirmation
if [[ "${confirmation}" != "RESTORE" ]]; then
  echo "Restore cancelled."
  exit 1
fi
postgres_url="${DIGITAL_TWIN_DATABASE_URL/postgresql+psycopg/postgresql}"
pg_restore --exit-on-error --no-owner --no-privileges \
  --dbname="${postgres_url}" "${dump_file}"
echo "Restore completed. Run bash deploy/lobot/start.sh."
