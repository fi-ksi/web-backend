#!/bin/bash
# Uninstall KSI Backend VM systemd service
# Run with: sudo ./uninstall-service.sh

set -e

SERVICE_NAME="ksi-backend-vm"
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"

if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo ./uninstall-service.sh)"
    exit 1
fi

echo "Uninstalling systemd service for KSI Backend VM..."

# Stop and disable service if running
systemctl stop "$SERVICE_NAME" 2>/dev/null || true
systemctl disable "$SERVICE_NAME" 2>/dev/null || true

# Remove service file
if [ -f "$SERVICE_FILE" ]; then
    rm -f "$SERVICE_FILE"
    echo "✓ Removed $SERVICE_FILE"
fi

# Reload systemd
systemctl daemon-reload

echo "✓ Service uninstalled"
