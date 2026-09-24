#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
RUN_DIR="$ROOT/.run"
NAME=ollama
source "$ROOT/../process.sh"
stop_process
