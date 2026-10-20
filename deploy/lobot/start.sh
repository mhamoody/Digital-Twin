#!/usr/bin/env bash
# Start the API and protected dashboard inside a Lobot/JupyterHub workspace.
set -euo pipefail
umask 077

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
for name in api dashboard worker; do
  pid_file="var/run/${name}.pid"
  if [[ -f "${pid_file}" ]] && kill -0 "$(cat "${pid_file}")" 2>/dev/null; then
    echo "${name} is already running with PID $(cat "${pid_file}")." >&2
    exit 1
  fi
done

source .venv/bin/activate
if [[ ! -f "${DIGITAL_TWIN_API_KEY_FILE:-var/auth/api.key}" ]]; then
  echo "Run bash deploy/lobot/upgrade_workspace.sh YOUR_USERNAME to initialize protected workspace access." >&2
  exit 1
fi
if [[ -f var/models/predictor.json ]]; then
  DIGITAL_TWIN_LLM_DIGEST="$(python -c 'import json; print(json.load(open("var/models/predictor.json"))["digest"])')"
  export DIGITAL_TWIN_LLM_DIGEST
fi
if [[ "${DIGITAL_TWIN_DATABASE_URL}" == sqlite* ]]; then
  python scripts/initialize_pilot_database.py
else
  python -m alembic upgrade head
fi

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

nohup python scripts/run_analysis_worker.py >var/log/worker.log 2>&1 &
echo $! >var/run/worker.pid

ready="false"
for _attempt in {1..20}; do
  if curl --fail --silent http://127.0.0.1:8000/health/ready >/dev/null 2>&1 \
    && curl --fail --silent http://127.0.0.1:8501/_stcore/health >/dev/null 2>&1 \
    && kill -0 "$(cat var/run/worker.pid)" 2>/dev/null; then
    ready="true"
    break
  fi
  sleep 1
done
if [[ "${ready}" != "true" ]]; then
  echo "A service did not become ready. Inspect var/log/api.log, dashboard.log and worker.log." >&2
  bash deploy/lobot/stop.sh
  exit 1
fi

echo "API and protected dashboard are ready."
echo "Analysis worker started. Model readiness is reported separately by model.sh status."
if [[ -n "${JUPYTERHUB_SERVICE_PREFIX:-}" ]]; then
  echo "Open: ${JUPYTERHUB_SERVICE_PREFIX}proxy/8501/"
else
  echo "No JupyterHub service prefix was detected. Use the hosting route supplied by Lobot."
fi
