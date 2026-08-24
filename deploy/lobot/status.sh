#!/usr/bin/env bash
# Display process and local health status without showing secrets.
set -u

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${project_root}"

for name in api dashboard; do
  pid_file="var/run/${name}.pid"
  if [[ -f "${pid_file}" ]] && kill -0 "$(cat "${pid_file}")" 2>/dev/null; then
    echo "${name}: running (PID $(cat "${pid_file}"))"
  else
    echo "${name}: stopped"
  fi
done
curl --fail --silent http://127.0.0.1:8000/health/ready 2>/dev/null || echo "API readiness: unavailable"
echo
curl --fail --silent http://127.0.0.1:8501/_stcore/health 2>/dev/null || echo "Dashboard health: unavailable"
echo
