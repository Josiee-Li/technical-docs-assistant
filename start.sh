#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
cd "$ROOT"
mode=${1:-cli}
[[ $# == 0 ]] || shift
case "$mode" in
    cli|web|frontend) ;;
    *) echo 'Usage: ./start.sh [cli [doc-assistant arguments...] | web | frontend]' >&2; exit 2 ;;
esac
if [[ ! -x .venv/bin/doc-assistant ]]; then
    echo 'Dependencies missing. Run: uv sync --extra dev' >&2
    exit 1
fi
RUN_DIR="$ROOT/.run"
if [[ $mode == cli ]]; then
    NAME=cli
    source "$ROOT/scripts/process.sh"
    [[ $# != 0 ]] || set -- chat
    start_process yes "$ROOT/.venv/bin/doc-assistant" "$@"
else
    [[ $# == 0 ]] || { echo 'Set PORT to configure the web port.' >&2; exit 2; }
    NAME=web
    PORT=${PORT:-8001}
    HEALTH_URL="http://127.0.0.1:$PORT/health"
    command -v curl >/dev/null
    source "$ROOT/scripts/process.sh"
    if ! running; then
        "$ROOT/.venv/bin/python" -c 'import socket, sys
try:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", int(sys.argv[1])))
except (OSError, ValueError, OverflowError) as exc:
    sys.exit(f"Cannot use port {sys.argv[1]}: {exc}. Set PORT to another port.")' "$PORT"
    fi
    start_process no "$ROOT/.venv/bin/uvicorn" doc_assistant.api:app --host 127.0.0.1 --port "$PORT"
    echo "Browser interface: http://127.0.0.1:$PORT/docs"
fi
