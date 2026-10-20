#!/usr/bin/env bash
# Back up and add the v2 pilot. Pass an existing account name for fictional courses.
set -euo pipefail
umask 077
project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${project_root}"
if [[ $# -ne 1 ]]; then
  echo "Usage: bash deploy/lobot/upgrade_workspace.sh EXISTING_USERNAME" >&2
  exit 1
fi
source .venv/bin/activate
set -a
source .env.lobot
set +a
bash deploy/lobot/backup.sh
bash deploy/lobot/stop.sh
python -m pip install --editable .
if [[ "${DIGITAL_TWIN_DATABASE_URL}" == sqlite* ]]; then
  python scripts/initialize_pilot_database.py
else
  python -m alembic upgrade head
fi
python scripts/prepare_workspace.py --grant-demo-access "$1" --baseline
echo "Upgrade complete; existing empirical records retained. Start model.sh and start.sh next."
