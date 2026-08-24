#!/usr/bin/env bash
# Create a compressed PostgreSQL backup and retain the newest seven copies.
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${project_root}"
env_file="${DIGITAL_TWIN_ENV_FILE:-${project_root}/.env.lobot}"
set -a
# shellcheck disable=SC1090
source "${env_file}"
set +a
: "${DIGITAL_TWIN_DATABASE_URL:?DIGITAL_TWIN_DATABASE_URL is required}"
command -v pg_dump >/dev/null 2>&1 || {
  echo "pg_dump is required for backups." >&2
  exit 1
}

mkdir -p var/backups
backup_file="var/backups/digital_twin_$(date -u +%Y%m%dT%H%M%SZ).dump"
postgres_url="${DIGITAL_TWIN_DATABASE_URL/postgresql+psycopg/postgresql}"
pg_dump --format=custom --file="${backup_file}" "${postgres_url}"
chmod 600 "${backup_file}" 2>/dev/null || true
mapfile -t old_backups < <(find var/backups -maxdepth 1 -type f -name 'digital_twin_*.dump' -printf '%T@ %p\n' | sort -rn | tail -n +8 | cut -d' ' -f2-)
if ((${#old_backups[@]})); then
  rm -- "${old_backups[@]}"
fi
echo "Backup created: ${backup_file}"
