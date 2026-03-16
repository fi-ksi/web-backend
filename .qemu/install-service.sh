#!/bin/bash
# Install KSI Backend VM as a systemd service
# Run with: ./install-service.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SERVICE_NAME="ksi-backend-vm"
TEMPLATE="$SCRIPT_DIR/ksi-backend-vm.service.template"
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"

if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo ./install-service.sh)"
    exit 1
fi

# Get the user who called sudo
REAL_USER="${SUDO_USER:-$USER}"
REAL_UID=$(id -u "$REAL_USER")

echo "Installing systemd service for KSI Backend VM..."
echo "  User: $REAL_USER (UID: $REAL_UID)"
echo "  Project: $PROJECT_DIR"

# Generate service file from template
sed -e "s|%USER%|$REAL_USER|g" \
    -e "s|%UID%|$REAL_UID|g" \
    -e "s|%PROJECT_DIR%|$PROJECT_DIR|g" \
    "$TEMPLATE" > "$SERVICE_FILE"

chmod 644 "$SERVICE_FILE"

# Reload systemd
systemctl daemon-reload

echo ""
echo "✓ Service installed: $SERVICE_NAME"
echo ""
echo "Usage:"
echo "  sudo systemctl start $SERVICE_NAME     # Start VM"
echo "  sudo systemctl stop $SERVICE_NAME      # Stop VM"
echo "  sudo systemctl restart $SERVICE_NAME   # Restart VM"
echo "  sudo systemctl status $SERVICE_NAME    # Check status"
echo "  sudo systemctl enable $SERVICE_NAME    # Start on boot"
echo "  sudo systemctl disable $SERVICE_NAME   # Disable start on boot"
echo ""
echo "View logs:"
echo "  journalctl -u $SERVICE_NAME -f"
