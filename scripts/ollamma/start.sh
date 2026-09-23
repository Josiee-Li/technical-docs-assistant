#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
OLLAMA_BIN=${OLLAMA_BIN:-$HOME/apps/ollama/bin/ollama}
[[ -x $OLLAMA_BIN ]] || { echo "Ollama executable not found: $OLLAMA_BIN" >&2; exit 1; }
export OLLAMA_HOST=${OLLAMA_HOST:-127.0.0.1:11434}
HEALTH_URL="${OLLAMA_HOST%/}/api/tags"
[[ $HEALTH_URL == http*://* ]] || HEALTH_URL="http://$HEALTH_URL"
command -v curl >/dev/null
RUN_DIR="$ROOT/.run"
NAME=ollama
source "$ROOT/process.sh"
if ! running && curl --noproxy '*' -fsS --max-time 2 "$HEALTH_URL" >/dev/null 2>&1; then
    echo "An existing Ollama service is available at $OLLAMA_HOST; it is not managed by these scripts."
    exit 0
fi
start_process no "$OLLAMA_BIN" serve
