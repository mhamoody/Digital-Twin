#!/usr/bin/env bash
# Create an isolated Python environment for the Lobot/JupyterHub pilot.
set -euo pipefail
umask 077

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${project_root}"

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install --editable .
mkdir -p var/auth var/run var/log var/backups var/data artifacts/lobot
chmod 700 var/auth var/backups var/data

echo "Bootstrap complete. Copy deploy/lobot/env.example to .env.lobot and fill it locally."
echo "Then create an instructor account with scripts/manage_instructor_accounts.py."
