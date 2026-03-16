#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VM_DIR="$SCRIPT_DIR/vms"
VM_NAME="ksi-backend"
PID_FILE="$VM_DIR/$VM_NAME.pid"
MONITOR_SOCK="$VM_DIR/$VM_NAME-monitor.sock"

echo "=== Stopping KSI Backend VM ==="

if [ ! -f "$PID_FILE" ]; then
    echo "VM does not appear to be running (no PID file)"
    exit 0
fi

PID=$(cat "$PID_FILE")

if ! ps -p "$PID" > /dev/null 2>&1; then
    echo "VM is not running (PID $PID not found)"
    rm -f "$PID_FILE"
    exit 0
fi

echo "Stopping VM (PID: $PID)..."

# Try graceful shutdown via QMP
if [ -S "$MONITOR_SOCK" ]; then
    {
        echo '{"execute": "qmp_capabilities"}'
        sleep 0.1
        echo '{"execute": "system_powerdown"}'
        sleep 0.1
    } | nc -U "$MONITOR_SOCK" 2>/dev/null || true
    
    # Wait for graceful shutdown
    for i in {1..30}; do
        if ! ps -p "$PID" > /dev/null 2>&1; then
            echo "✓ VM stopped gracefully"
            rm -f "$PID_FILE"
            exit 0
        fi
        sleep 1
    done
fi

# Force kill if still running
if ps -p "$PID" > /dev/null 2>&1; then
    echo "Forcing VM shutdown..."
    kill -9 "$PID" 2>/dev/null || true
fi

rm -f "$PID_FILE"
echo "✓ VM stopped"
