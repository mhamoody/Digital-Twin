#!/usr/bin/env bash
# Manage only our private model process. No public model port, Docker or sudo.
set -euo pipefail
umask 077
project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${project_root}"
source .venv/bin/activate
if [[ -f .env.lobot ]]; then
  set -a
  source .env.lobot
  set +a
fi
mkdir -p var/run var/log var/models var/tools
export OLLAMA_HOST="127.0.0.1:11434"
export OLLAMA_NO_CLOUD=1
export OLLAMA_MODELS="${project_root}/var/models"
export OLLAMA_NUM_PARALLEL=1
export OLLAMA_MAX_LOADED_MODELS=1
export OLLAMA_CONTEXT_LENGTH="${DIGITAL_TWIN_LLM_CONTEXT:-8192}"
export OLLAMA_KEEP_ALIVE=10m
model="${DIGITAL_TWIN_LLM_MODEL:-qwen2.5:7b}"
if [[ "${model}" != "qwen2.5:7b" ]]; then
  echo "Unapproved predictor model; expected qwen2.5:7b." >&2
  exit 1
fi
action="${1:-status}"
if [[ "${action}" == install ]]; then
  if ! command -v ollama >/dev/null 2>&1 && [[ ! -f var/tools/ollama-path.txt ]]; then
    python -m pip install 'zstandard>=0.23,<1'
    python scripts/install_ollama_local.py
  fi
fi
if [[ -f var/tools/ollama-path.txt ]]; then
  ollama_binary="$(<var/tools/ollama-path.txt)"
elif command -v ollama >/dev/null 2>&1; then
  ollama_binary="$(command -v ollama)"
else
  echo "Ollama is not installed. Run: bash deploy/lobot/model.sh install" >&2
  exit 1
fi
if [[ "${action}" == install || "${action}" == start ]]; then
  if ! curl --fail --silent --max-time 3 http://127.0.0.1:11434/api/tags >/dev/null; then
    nohup "${ollama_binary}" serve >var/log/ollama.log 2>&1 &
    echo $! >var/run/ollama.pid
    ready=false
    for _attempt in {1..30}; do
      if curl --fail --silent --max-time 2 http://127.0.0.1:11434/api/tags >/dev/null; then
        ready=true
        break
      fi
      sleep 1
    done
    if [[ "${ready}" != true ]]; then
      echo "Model service failed to start; inspect var/log/ollama.log." >&2
      exit 1
    fi
  else
    echo "An Ollama service is already listening locally; reusing it without changing its process."
  fi
fi
if [[ "${action}" == install ]]; then
  "${ollama_binary}" pull "${model}"
  python - <<'PY'
import json
from pathlib import Path
from digital_twin.workspace.llm import OllamaClient
ready = OllamaClient().readiness()
if ready['status'] != 'ready':
    raise SystemExit('Approved model is not ready after installation.')
Path('var/models/predictor.json').write_text(json.dumps(ready, indent=2))
print('Approved model installed; digest recorded in ignored var/models/predictor.json.')
PY
fi
if [[ "${action}" == status || "${action}" == start || "${action}" == install ]]; then
  "${ollama_binary}" ps
  python - <<'PY'
from digital_twin.workspace.llm import OllamaClient
print(OllamaClient().readiness())
PY
elif [[ "${action}" == stop ]]; then
  if [[ -f var/run/ollama.pid ]]; then
    pid="$(<var/run/ollama.pid)"
    if [[ "${pid}" =~ ^[0-9]+$ ]] && kill -0 "${pid}" 2>/dev/null; then
      command_line="$(ps -p "${pid}" -o args= 2>/dev/null || true)"
      if [[ "${command_line}" == *ollama*serve* ]]; then
        kill "${pid}"
      else
        echo "PID belongs to another process; left untouched." >&2
        exit 1
      fi
    fi
    rm -f -- var/run/ollama.pid
  fi
else
  echo "Usage: bash deploy/lobot/model.sh install|start|status|stop" >&2
  exit 1
fi
