#!/bin/bash
# Hermes-MemOS-gbrain Bridge Cron Wrapper
# Runs incremental sync with lock protection and logging

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRIDGE_HOME="${BRIDGE_HOME:-$HOME/.hermes/memos-plugin}"
LOG_FILE="${BRIDGE_HOME}/logs/bridge-sync.log"
LOCK_FILE="${BRIDGE_HOME}/scripts/.bridge.lock"

# Create directories
mkdir -p "$(dirname "$LOG_FILE")" "$(dirname "$LOCK_FILE")"

# Prevent concurrent runs
if [ -f "$LOCK_FILE" ]; then
    PID=$(cat "$LOCK_FILE" 2>/dev/null || echo "")
    if [ -n "$PID" ] && ps -p "$PID" > /dev/null 2>&1; then
        echo "[$(date)] Bridge already running (PID: $PID), skipping" >> "$LOG_FILE"
        exit 0
    fi
fi
echo $$ > "$LOCK_FILE"

trap 'rm -f "$LOCK_FILE"' EXIT

echo "[$(date)] Starting bridge sync..." >> "$LOG_FILE"

# Run bridge with auto-discovery and incremental sync
python3 "$SCRIPT_DIR/bridge.py" \
    --auto-discover \
    >> "$LOG_FILE" 2>&1

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "[$(date)] Bridge sync completed successfully" >> "$LOG_FILE"
else
    echo "[$(date)] Bridge sync failed with exit code $EXIT_CODE" >> "$LOG_FILE"
fi

echo "" >> "$LOG_FILE"
exit $EXIT_CODE
