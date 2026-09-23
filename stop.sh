#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
case "${1:-all}" in
    all) names=(cli web) ;;
    cli) names=(cli) ;;
    web|frontend) names=(web) ;;
    *) echo 'Usage: ./stop.sh [all | cli | web | frontend]' >&2; exit 2 ;;
esac
result=0
for name in "${names[@]}"; do
    (
        RUN_DIR="$ROOT/.run"
        NAME=$name
        source "$ROOT/scripts/process.sh"
        stop_process
    ) || result=1
done
exit "$result"
