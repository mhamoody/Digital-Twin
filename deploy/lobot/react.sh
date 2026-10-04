#!/usr/bin/env bash
# Parallel React/API process only. Never starts/stops the original worker or UI.
set -euo pipefail
umask 077
react_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
operation="${1:-status}"
if [[ "${operation}" == build ]]; then
  cd "${react_root}/frontend"
  node -e 'const [a,b]=process.versions.node.split(".").map(Number); if(a<22 || (a===22&&b<12)){console.error("Node >=22.12 required. Alternatively build locally and transfer frontend/dist.");process.exit(1)}'
  npm ci
  npm run build
  exit 0
fi
case "${operation}" in start|status|stop) ;; *) echo "Usage: bash deploy/lobot/react.sh {build|start|status|stop}" >&2; exit 2;; esac
shared_root="${DIGITAL_TWIN_SHARED_ROOT:-$(dirname "${react_root}")/Digital-Twin}"
shared_root="$(cd "${shared_root}" && pwd)"
if [[ ! -x "${shared_root}/.venv/bin/python" || ! -f "${shared_root}/.env.lobot" ]]; then
  echo "Existing shared environment/venv not found. Set DIGITAL_TWIN_SHARED_ROOT to the original Digital-Twin directory." >&2
  exit 1
fi
cd "${shared_root}"
set -a
# Existing trusted deployment configuration, never printed or rewritten.
source "${shared_root}/.env.lobot"
set +a
: "${DIGITAL_TWIN_DATABASE_URL:?Existing database URL is required}"
: "${DIGITAL_TWIN_AUTH_FILE:?Existing instructor account file is required}"
export DIGITAL_TWIN_BROWSER_ENABLED=1
export DIGITAL_TWIN_BROWSER_ORIGIN=https://lobot.cs.queensu.ca
export DIGITAL_TWIN_BROWSER_SECURE=1
export DIGITAL_TWIN_BROWSER_PATH=/user/group-digi2026-g12/proxy/8502/
export DIGITAL_TWIN_FRONTEND_DIST="${react_root}/frontend/dist"
export DIGITAL_TWIN_REACT_SHARED_ROOT="${shared_root}"
if [[ -f var/models/predictor.json ]]; then
  DIGITAL_TWIN_LLM_DIGEST="$(.venv/bin/python -c 'import json; print(json.load(open("var/models/predictor.json"))["digest"])')"
  export DIGITAL_TWIN_LLM_DIGEST
fi
exec .venv/bin/python "${react_root}/scripts/manage_react_server.py" "${operation}" --root "${react_root}" --shared-root "${shared_root}"
