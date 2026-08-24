#!/usr/bin/env bash
# Collect non-secret facts needed to choose a safe Lobot deployment profile.
set -u

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
output_dir="${project_root}/artifacts/lobot"
output_file="${output_dir}/probe.txt"
mkdir -p "${output_dir}"

has_command() {
  if command -v "$1" >/dev/null 2>&1; then
    printf '%-24s %s\n' "$1" "available"
  else
    printf '%-24s %s\n' "$1" "not found"
  fi
}

{
  echo "Digital Twin Lobot capability probe"
  echo "Generated (UTC): $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "Kernel: $(uname -srm 2>/dev/null || echo unavailable)"
  echo "Python: $(python3 --version 2>&1 || echo not found)"
  echo "Working filesystem: $(df -h "${project_root}" 2>/dev/null | tail -n 1 || echo unavailable)"
  echo
  echo "Commands"
  for candidate in git curl python3 pip3 docker podman psql pg_dump systemctl tmux; do
    has_command "${candidate}"
  done
  echo
  echo "Python modules"
  python3 - <<'PY' 2>/dev/null || true
import importlib.util

for name in ("jupyter_server_proxy", "fastapi", "streamlit", "sqlalchemy", "psycopg"):
    state = "available" if importlib.util.find_spec(name) else "not found"
    print(f"{name:24} {state}")
PY
  echo
  echo "JupyterHub routing"
  echo "JUPYTERHUB_SERVICE_PREFIX: ${JUPYTERHUB_SERVICE_PREFIX:-not set}"
  echo "JUPYTERHUB_USER: ${JUPYTERHUB_USER:-not set}"
  echo "JUPYTERHUB_SERVER_NAME: ${JUPYTERHUB_SERVER_NAME:-not set}"
  echo
  echo "Local listening ports (process details omitted)"
  if command -v ss >/dev/null 2>&1; then
    ss -ltnH 2>/dev/null | awk '{print $4}' | sed 's/.*://' | sort -nu
  else
    echo "ss not found"
  fi
} >"${output_file}"

echo "Probe written to ${output_file}"
echo "It contains capability names and routing metadata, never environment variable values or passwords."
