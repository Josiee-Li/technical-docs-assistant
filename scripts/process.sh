#!/usr/bin/env bash
# Linux process identity includes start time to avoid stopping a reused PID.
set -euo pipefail
mkdir -p "$RUN_DIR"
exec 9>"$RUN_DIR/$NAME.lock"
flock -x 9
PID_FILE="$RUN_DIR/$NAME.pid"
LOG_FILE="$RUN_DIR/$NAME.log"

identity() {
    local stat
    [[ -r /proc/$1/stat ]] || return 1
    stat=$(<"/proc/$1/stat")
    stat=${stat##*) }
    local fields=($stat)
    [[ ${fields[0]} != Z ]] || return 1
    printf '%s' "${fields[19]}"
}

running() {
    [[ -f $PID_FILE ]] || return 1
    read -r pid born < "$PID_FILE" || return 1
    [[ $pid =~ ^[0-9]+$ && $born =~ ^[0-9]+$ ]] || return 1
    [[ $(identity "$pid") == "$born" ]]
}

stop_process() {
    if ! running; then
        rm -f "$PID_FILE"
        echo "$NAME is not running (no managed process)."
        return
    fi
    kill -TERM "$pid"
    for ((i=0; i<100; i++)); do
        if ! running; then
            rm -f "$PID_FILE"
            echo "$NAME stopped."
            return
        fi
        sleep 0.1
    done
    echo "$NAME has not stopped yet; PID $pid retained. Try again later." >&2
    return 1
}

start_process() {
    local foreground=$1
    shift
    if running; then
        echo "$NAME is already running (PID $pid)."
        return
    fi
    if [[ $foreground == yes ]]; then
        printf '%s %s\n' "$$" "$(identity "$$")" > "$PID_FILE"
        flock -u 9
        exec 9>&-
        exec "$@"
    fi
    nohup "$@" </dev/null >>"$LOG_FILE" 2>&1 9>&- &
    pid=$!
    if ! born=$(identity "$pid"); then
        kill -TERM "$pid" 2>/dev/null || true
        wait "$pid" 2>/dev/null || true
        echo 'Cannot track process in /proc; run in a normal Linux host environment.' >&2
        return 1
    fi
    printf '%s %s\n' "$pid" "$born" > "$PID_FILE"
    for ((i=0; i<100; i++)); do
        if ! running; then
            rm -f "$PID_FILE"
            echo "$NAME failed to start. See $LOG_FILE" >&2
            return 1
        fi
        if curl --noproxy '*' -fsS --max-time 1 "$HEALTH_URL" >/dev/null 2>&1; then
            sleep 0.3
            if running; then
                echo "$NAME started (PID $pid). Log: $LOG_FILE"
                return
            fi
        fi
        sleep 0.2
    done
    echo "$NAME did not become ready. See $LOG_FILE" >&2
    stop_process
    return 1
}
