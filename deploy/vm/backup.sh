#!/usr/bin/env bash
# Back up the containerized PostgreSQL service to a host-side ignored directory.
set -euo pipefail

deployment_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd "${deployment_dir}/../.." && pwd)"
cd "${deployment_dir}"
mkdir -p "${project_root}/var/backups"
backup_file="${project_root}/var/backups/digital_twin_$(date -u +%Y%m%dT%H%M%SZ).dump"
docker compose --env-file .env.vm exec -T db \
  pg_dump --username digital_twin --dbname course_digital_twin --format=custom \
  >"${backup_file}"
chmod 600 "${backup_file}" 2>/dev/null || true
echo "Backup created: ${backup_file}"
