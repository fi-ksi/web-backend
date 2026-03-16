# QEMU Setup for KSI Backend

Run KSI Backend in a lightweight QEMU virtual machine without requiring root access on the host.

## Prerequisites

```bash
sudo apt install qemu-system-x86 qemu-utils cloud-image-utils
```

For KVM acceleration (recommended):
```bash
sudo usermod -aG kvm $USER
# Log out and back in
```

## Quick Start

```bash
# 1. Setup VM (downloads Debian 12 image, ~5 minutes)
.qemu/qemu-setup.sh

# 2. Start the VM
.qemu/qemu-start.sh

# 3. Wait 2-3 minutes for provisioning, then access:
# Backend: http://localhost:3030
```

The master account is `admin@localhost` with password `change-me`.

## Files

| File | Description |
|------|-------------|
| `qemu-setup.sh` | Downloads Debian image, creates VM disk and cloud-init seed |
| `qemu-start.sh` | Starts the VM with KVM and shared folders |
| `qemu-stop.sh` | Gracefully stops the VM |
| `qemu-status.sh` | Shows VM status |
| `install-service.sh` | Installs systemd service (run with sudo) |
| `uninstall-service.sh` | Removes systemd service |
| `ksi-backend-vm.service.template` | Systemd service template |
| `vms/` | VM disk images and runtime files |

## What Happens Automatically

When the VM boots, cloud-init:
1. Installs Docker and docker-compose
2. Mounts project directory at `/mnt/project` (via virtio-9p)
3. Runs `docker-compose build ksi-be`
4. Runs `docker-compose up -d ksi-be`

## Commands

### Start/Stop VM

```bash
.qemu/qemu-start.sh             # Start headless
.qemu/qemu-start.sh --gui       # Start with display window
.qemu/qemu-start.sh --console   # Start with serial console
.qemu/qemu-stop.sh              # Stop VM
.qemu/qemu-status.sh            # Check status
```

### Serial Console Access

Start the VM with `--console` flag to enable serial console:

```bash
.qemu/qemu-start.sh --console
```

Connect using `socat`:
```bash
socat - UNIX-CONNECT:.qemu/vms/ksi-backend-console.sock
```

Or with `minicom`:
```bash
minicom -D unix#.qemu/vms/ksi-backend-console.sock
```

Press Enter to get a login prompt. To disconnect:
- **socat**: `Ctrl+C`
- **minicom**: `Ctrl+A` then `X`

### Login to VM

If you enabled `--gui`, login at the display:
- **Username**: `debian`
- **Password**: `debian`

## Run as Systemd Service

To run the VM as a system service with auto-restart:

```bash
sudo .qemu/install-service.sh
```

Then use:
```bash
sudo systemctl start ksi-backend-vm    # Start
sudo systemctl stop ksi-backend-vm     # Stop
sudo systemctl enable ksi-backend-vm   # Start on boot
sudo systemctl status ksi-backend-vm   # Status
journalctl -u ksi-backend-vm -f        # Logs
```

To remove:
```bash
sudo .qemu/uninstall-service.sh
```

## Configuration

### Resource Allocation

Edit `qemu-start.sh`:
```bash
-smp cpus=2   # CPU cores (default: 1)
-m 1500M       # RAM (default: 800MB)
```

Edit `qemu-setup.sh`:
```bash
IMAGE_SIZE="30G"  # Disk size (default: 6GB)
```

### Port Forwarding

Edit `qemu-start.sh` to change or add ports:
```bash
-nic user,hostfwd=tcp:127.0.0.1:3030-:3030,hostfwd=tcp:127.0.0.1:2222-:22
```

## Shared Folders

The project directory is automatically shared:
- **Host**: `/path/to/web-backend`
- **Guest**: `/mnt/project`

Changes on host are immediately visible in the VM.

## Troubleshooting

### VM won't start
```bash
# Check logs
tail -f .qemu/vms/ksi-backend.log

# Verify KVM access
ls -la /dev/kvm
```

### No KVM acceleration
```bash
sudo usermod -aG kvm $USER
# Log out and back in
```

### Backend not responding
Wait 2-3 minutes for Docker to build and start. Check progress:
```bash
.qemu/qemu-start.sh --gui
# Login as debian/debian and run:
systemctl status ksi-backend
docker-compose logs
```

### Reset VM completely
```bash
.qemu/qemu-stop.sh
rm -rf .qemu/vms/
.qemu/qemu-setup.sh
.qemu/qemu-start.sh
```

## Resource Usage

- **Disk**: ~4-5 GB after provisioning
- **RAM**: 800 MB (configurable)
- **CPU**: 1 core (configurable)