#!/usr/bin/env bash
# Preserve evidence, logs and queues while installing the reliability correction.
set -euo pipefail
umask 077
project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${project_root}"
source .venv/bin/activate
set -a
source .env.lobot
set +a
backup_logs="artifacts/lobot/log-backups/$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "${backup_logs}"
for name in worker api dashboard ollama; do
  if [[ -f "var/log/${name}.log" ]]; then
    cp -p -- "var/log/${name}.log" "${backup_logs}/${name}.log"
  fi
done
bash deploy/lobot/backup.sh
stopped=false
for _attempt in {1..65}; do
  if bash deploy/lobot/stop.sh; then stopped=true; break; fi
  sleep 2
done
if [[ "${stopped}" != true ]]; then
  echo "Worker did not stop safely. No code/database upgrade was attempted." >&2
  exit 1
fi
python -m pip install --editable .
if [[ "${DIGITAL_TWIN_DATABASE_URL}" == sqlite* ]]; then
  python scripts/initialize_pilot_database.py
else
  python -m alembic upgrade head
fi
bash deploy/lobot/start.sh
echo "Reliability update installed; existing course pauses and analysis history are preserved."
echo "An old global validation pause is isolated to its responsible course on worker startup."
echo "No scores were replaced and no model accuracy result is implied."
