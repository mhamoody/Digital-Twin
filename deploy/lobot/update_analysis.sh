#!/usr/bin/env bash
# Add automatic analysis without regenerating empirical/synthetic data or model weights.
set -euo pipefail
umask 077
project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${project_root}"
source .venv/bin/activate
set -a
source .env.lobot
set +a
bash deploy/lobot/backup.sh
echo "Stopping the worker safely; an in-flight model request may need time to finish."
stopped=false
for _attempt in {1..30}; do
  if bash deploy/lobot/stop.sh; then
    stopped=true
    break
  fi
  sleep 2
done
if [[ "${stopped}" != true ]]; then
  echo "Services did not stop safely. No application/database upgrade was attempted." >&2
  exit 1
fi
python -m pip install --editable .
if [[ "${DIGITAL_TWIN_DATABASE_URL}" == sqlite* ]]; then
  python scripts/initialize_pilot_database.py
else
  python -m alembic upgrade head
fi
bash deploy/lobot/start.sh
echo "Automatic analysis enabled by default per course; existing settings are preserved."
echo "If the model is stopped, run: bash deploy/lobot/model.sh start"
echo "Use the all-checkpoints analysis panel to inspect progress, causes, and eligible retries."
