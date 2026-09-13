#!/usr/bin/env bash
# Display process and local health status without showing secrets.
set -u

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${project_root}"

for name in api dashboard worker; do
  pid_file="var/run/${name}.pid"
  if [[ -f "${pid_file}" ]] && kill -0 "$(cat "${pid_file}")" 2>/dev/null; then
    echo "${name}: running (PID $(cat "${pid_file}"))"
  else
    echo "${name}: stopped"
  fi
done
curl --fail --silent http://127.0.0.1:8000/health/ready 2>/dev/null || echo "API readiness: unavailable"
echo
curl --fail --silent --max-time 3 http://127.0.0.1:11434/api/tags >/dev/null 2>&1 \
  && echo "Model runtime: reachable (check model.sh status for approved model)" \
  || echo "Model runtime: unavailable (saved results and case management remain usable)"
curl --fail --silent http://127.0.0.1:8501/_stcore/health 2>/dev/null || echo "Dashboard health: unavailable"
echo
