#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VM_DIR="$SCRIPT_DIR/vms"
VM_NAME="ksi-backend"
PID_FILE="$VM_DIR/$VM_NAME.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "VM is not running"
    exit 1
fi

PID=$(cat "$PID_FILE")

if ! ps -p "$PID" > /dev/null 2>&1; then
    echo "VM is not running (PID $PID not found)"
    exit 1
fi

echo "VM is running (PID: $PID)"
echo ""
echo "Port forwarding:"
echo "  Backend:       localhost:3030"
