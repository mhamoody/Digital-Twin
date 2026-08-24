#!/usr/bin/env bash
# Stop only the project processes recorded by start.sh.
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${project_root}"

for name in dashboard api; do
  pid_file="var/run/${name}.pid"
  if [[ ! -f "${pid_file}" ]]; then
    echo "${name}: no PID file"
    continue
  fi
  pid="$(cat "${pid_file}")"
  if [[ "${pid}" =~ ^[0-9]+$ ]] && kill -0 "${pid}" 2>/dev/null; then
    command_line="$(ps -p "${pid}" -o args= 2>/dev/null || true)"
    if [[ "${command_line}" == *"digital_twin.api.app"* || "${command_line}" == *"dashboard/app.py"* ]]; then
      kill "${pid}"
      echo "${name}: stopped PID ${pid}"
    else
      echo "${name}: PID ${pid} does not belong to this project; left untouched" >&2
    fi
  else
    echo "${name}: not running"
  fi
  rm -f "${pid_file}"
done
