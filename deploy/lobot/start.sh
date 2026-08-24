#!/usr/bin/env bash
# Start the API and protected dashboard inside a Lobot/JupyterHub workspace.
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${project_root}"
env_file="${DIGITAL_TWIN_ENV_FILE:-${project_root}/.env.lobot}"

if [[ ! -f "${env_file}" ]]; then
  echo "Missing ${env_file}. Copy deploy/lobot/env.example and fill its placeholders." >&2
  exit 1
fi
set -a
# shellcheck disable=SC1090
source "${env_file}"
set +a

: "${DIGITAL_TWIN_DATABASE_URL:?DIGITAL_TWIN_DATABASE_URL is required}"
: "${DIGITAL_TWIN_AUTH_FILE:?DIGITAL_TWIN_AUTH_FILE is required}"
if [[ ! -f "${DIGITAL_TWIN_AUTH_FILE}" ]]; then
  echo "Instructor account file not found: ${DIGITAL_TWIN_AUTH_FILE}" >&2
  exit 1
fi
if [[ ! -x .venv/bin/python ]]; then
  echo "Run bash deploy/lobot/bootstrap.sh first." >&2
  exit 1
fi

mkdir -p var/run var/log
for name in api dashboard; do
  pid_file="var/run/${name}.pid"
  if [[ -f "${pid_file}" ]] && kill -0 "$(cat "${pid_file}")" 2>/dev/null; then
    echo "${name} is already running with PID $(cat "${pid_file}")." >&2
    exit 1
  fi
done

source .venv/bin/activate
python -m alembic upgrade head

export DIGITAL_TWIN_API_URL="http://127.0.0.1:8000"
nohup python -m uvicorn digital_twin.api.app:app \
  --app-dir src --host 127.0.0.1 --port 8000 \
  >var/log/api.log 2>&1 &
echo $! >var/run/api.pid

nohup python -m streamlit run src/digital_twin/dashboard/app.py \
  --server.address 127.0.0.1 --server.port 8501 --server.headless true \
  --browser.gatherUsageStats false \
  >var/log/dashboard.log 2>&1 &
echo $! >var/run/dashboard.pid

ready="false"
for _attempt in {1..20}; do
  if curl --fail --silent http://127.0.0.1:8000/health/ready >/dev/null 2>&1 \
    && curl --fail --silent http://127.0.0.1:8501/_stcore/health >/dev/null 2>&1; then
    ready="true"
    break
  fi
  sleep 1
done
if [[ "${ready}" != "true" ]]; then
  echo "A service did not become ready. Inspect var/log/api.log and var/log/dashboard.log." >&2
  bash deploy/lobot/stop.sh
  exit 1
fi

echo "API and protected dashboard are ready."
if [[ -n "${JUPYTERHUB_SERVICE_PREFIX:-}" ]]; then
  echo "Open: ${JUPYTERHUB_SERVICE_PREFIX}proxy/8501/"
else
  echo "No JupyterHub service prefix was detected. Use the hosting route supplied by Lobot."
fi
