#!/bin/bash
set -e

# ============================================================================
# Environment Variables (configurable via KSI_* env vars)
# ============================================================================
BACKEND_PORT="${KSI_PORT:-3030}"
BACKEND_HOST="${KSI_HOST:-127.0.0.1}"
DATA_DIR="${KSI_DATA_DIR:-}"

# ============================================================================
# Internal Configuration
# ============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VM_DIR="$SCRIPT_DIR/vms"
VM_NAME="ksi-backend"
IMAGE="$VM_DIR/$VM_NAME.qcow2"
SEED_IMAGE="$VM_DIR/seed.iso"
PID_FILE="$VM_DIR/$VM_NAME.pid"
MONITOR_SOCK="$VM_DIR/$VM_NAME-monitor.sock"
QEMU_LOG="$VM_DIR/$VM_NAME.log"
CONSOLE_SOCK="$VM_DIR/$VM_NAME-console.sock"
DISPLAY_OPT="-display none"
CONSOLE_OPT=""

# Use default data directory if not specified
if [ -z "$DATA_DIR" ]; then
    DATA_DIR="$SCRIPT_DIR/data"
fi

# Parse command line arguments
for arg in "$@"; do
    case "$arg" in
        --gui)
            DISPLAY_OPT="-display gtk"
            ;;
        --console)
            CONSOLE_OPT="-serial unix:$CONSOLE_SOCK,server,nowait"
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --gui      Enable graphical display (GTK)"
            echo "  --console  Enable serial console (socket: $CONSOLE_SOCK)"
            echo "  -h, --help Show this help message"
            exit 0
            ;;
    esac
done

# Check if images exist
if [ ! -f "$IMAGE" ]; then
    echo "Error: VM image not found. Run 'qemu-setup.sh' first"
    exit 1
fi

if [ ! -f "$SEED_IMAGE" ]; then
    echo "Error: Seed image not found. Run 'qemu-setup.sh' first"
    exit 1
fi

# Check if VM is already running
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "VM is already running (PID: $PID)"
        echo "To stop it, run: $SCRIPT_DIR/qemu-stop.sh"
        exit 0
    fi
fi

echo "=== Starting KSI Backend VM ==="

# Check if KVM is available
if [ ! -e /dev/kvm ]; then
    echo "Warning: /dev/kvm not found. KVM acceleration not available."
    echo "VM will run slower without KVM."
    KVM_OPTS=""
else
    if [ ! -r /dev/kvm ] || [ ! -w /dev/kvm ]; then
        echo "Warning: No permission to access /dev/kvm"
        echo "Add yourself to the kvm group: sudo usermod -aG kvm $USER"
        KVM_OPTS=""
    else
        KVM_OPTS="-enable-kvm"
    fi
fi

# Project directory to share with VM
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Create data directories
mkdir -p "$DATA_DIR/seminar.git" "$DATA_DIR/data" "$DATA_DIR/db"

# Start QEMU with KVM optimization
qemu-system-x86_64 \
    -name "$VM_NAME" \
    $KVM_OPTS \
    -machine type=q35 \
    -cpu host \
    -smp cpus=1 \
    -m 800M \
    -drive file="$IMAGE",format=qcow2,if=virtio,cache=writeback \
    -drive file="$SEED_IMAGE",format=raw,if=virtio \
    -nic user,hostfwd=tcp:$BACKEND_HOST:$BACKEND_PORT-:3030 \
    -virtfs local,path="$PROJECT_DIR",mount_tag=project,security_model=mapped-xattr,id=project \
    -virtfs local,path="$DATA_DIR/seminar.git",mount_tag=seminar_git,security_model=mapped-xattr,id=seminar_git \
    -virtfs local,path="$DATA_DIR/data",mount_tag=opt_data,security_model=mapped-xattr,id=opt_data \
    -virtfs local,path="$DATA_DIR/db",mount_tag=opt_db,security_model=mapped-xattr,id=opt_db \
    $CONSOLE_OPT \
    $DISPLAY_OPT \
    -qmp unix:"$MONITOR_SOCK",server,nowait \
    -pidfile "$PID_FILE" \
    -daemonize \
    -device virtio-balloon \
    -device qemu-xhci \
    -device usb-tablet \
    >> "$QEMU_LOG" 2>&1 &

sleep 2

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    echo "✓ VM started with PID: $PID"
    echo ""
    echo "Port forwarding:"
    echo "  Backend:       localhost:$BACKEND_PORT"
    echo ""
    if [ -n "$CONSOLE_OPT" ]; then
        echo "Console socket: $CONSOLE_SOCK"
        echo "  Connect with: socat - UNIX-CONNECT:$CONSOLE_SOCK"
        echo ""
    fi
    echo "Shared folder:"
    echo "  Host:  $PROJECT_DIR"
    echo "  Guest: /mnt/project"
    echo ""
    echo "Cloud-init is provisioning the VM (1-3 minutes)..."
    echo "Docker compose will start automatically after provisioning."
    echo ""
    echo "Monitor progress: tail -f $QEMU_LOG"
else
    echo "Error: Failed to start VM"
    exit 1
fi
