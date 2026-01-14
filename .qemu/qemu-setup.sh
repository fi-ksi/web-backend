#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VM_DIR="$SCRIPT_DIR/vms"
VM_NAME="ksi-backend"
IMAGE="$VM_DIR/$VM_NAME.qcow2"
SEED_IMAGE="$VM_DIR/seed.iso"

# Configuration
IMAGE_SIZE="6G"  # Used approx 4.3 GB after provisioning
# Debian 12 cloud image
IMAGE_URL="https://cloud.debian.org/images/cloud/bookworm/latest/debian-12-generic-amd64.qcow2"

mkdir -p "$VM_DIR"

echo "=== Downloading Debian 12 cloud image ==="
if [ ! -f "$VM_DIR/debian-12-base.qcow2" ]; then
    cd "$VM_DIR"
    wget -q --show-progress "$IMAGE_URL" -O debian-12-base.qcow2
    cd - > /dev/null
fi

echo "=== Creating VM disk image ==="
if [ ! -f "$IMAGE" ]; then
    qemu-img create -f qcow2 -b "$VM_DIR/debian-12-base.qcow2" -F qcow2 "$IMAGE" "$IMAGE_SIZE"
else
    echo "Image already exists: $IMAGE"
fi

echo "=== Creating cloud-init seed image ==="
if [ ! -f "$SEED_IMAGE" ]; then
    cat > "$VM_DIR/user-data" <<'EOF'
#cloud-config
hostname: ksi-backend
fqdn: ksi-backend.local
users:
  - name: debian
    sudo: ALL=(ALL) NOPASSWD:ALL
    shell: /bin/bash
    lock_passwd: false
packages:
  - curl
  - wget
  - git
  - docker.io
  - docker-compose
  - rsync
growpart:
  mode: auto
  devices: ["/"]
write_files:
  - path: /usr/local/bin/ksi-patch-compose.sh
    permissions: '0755'
    content: |
      #!/bin/bash
      # Patch docker-compose.yaml to use QEMU host-mounted paths
      COMPOSE_FILE="$1"
      if [ -z "$COMPOSE_FILE" ]; then
        echo "Usage: $0 <docker-compose.yaml>"
        exit 1
      fi
      sed -i \
        -e 's|ksi-backend-data:/opt/data|/mnt/data/data:/opt/data|' \
        -e 's|ksi-backend-db:/opt/database|/mnt/data/db:/opt/database|' \
        -e 's|./.docker/data/seminar.git:/opt/seminar.git|/mnt/data/seminar.git:/opt/seminar.git|' \
        "$COMPOSE_FILE"
  - path: /etc/systemd/system/ksi-backend.service
    content: |
      [Unit]
      Description=KSI Backend Docker Compose
      Requires=docker.service
      After=docker.service mnt-project.mount mnt-data-seminar.git.mount mnt-data-data.mount mnt-data-db.mount
      
      [Service]
      Type=oneshot
      RemainAfterExit=yes
      WorkingDirectory=/mnt/project
      ExecStartPre=/usr/local/bin/ksi-patch-compose.sh /mnt/project/docker-compose.yaml
      ExecStart=/bin/bash -c '/usr/bin/docker-compose build ksi-be && /usr/bin/docker-compose up -d ksi-be'
      ExecStop=/usr/bin/docker-compose down ksi-be
      
      [Install]
      WantedBy=multi-user.target
  - path: /etc/systemd/system/mnt-project.mount
    content: |
      [Unit]
      Description=Mount project directory from host
      
      [Mount]
      What=project
      Where=/mnt/project
      Type=9p
      Options=trans=virtio,version=9p2000.L,rw
      
      [Install]
      WantedBy=multi-user.target
  - path: /etc/systemd/system/mnt-data-seminar.git.mount
    content: |
      [Unit]
      Description=Mount seminar.git directory from host
      
      [Mount]
      What=seminar_git
      Where=/mnt/data/seminar.git
      Type=9p
      Options=trans=virtio,version=9p2000.L,rw
      
      [Install]
      WantedBy=multi-user.target
  - path: /etc/systemd/system/mnt-data-data.mount
    content: |
      [Unit]
      Description=Mount data directory from host
      
      [Mount]
      What=opt_data
      Where=/mnt/data/data
      Type=9p
      Options=trans=virtio,version=9p2000.L,rw
      
      [Install]
      WantedBy=multi-user.target
  - path: /etc/systemd/system/mnt-data-db.mount
    content: |
      [Unit]
      Description=Mount database directory from host
      
      [Mount]
      What=opt_db
      Where=/mnt/data/db
      Type=9p
      Options=trans=virtio,version=9p2000.L,rw
      
      [Install]
      WantedBy=multi-user.target
runcmd:
  - echo 'debian:debian' | chpasswd
  - systemctl disable ssh
  - systemctl stop ssh
  - systemctl enable docker
  - systemctl start docker
  - echo "kernel.unprivileged_userns_clone=1" >> /etc/sysctl.conf
  - sysctl -p
  - mkdir -p /mnt/project
  - mkdir -p /mnt/data/seminar.git /mnt/data/data /mnt/data/db
  - systemctl daemon-reload
  - systemctl enable mnt-project.mount
  - systemctl start mnt-project.mount
  - systemctl enable mnt-data-seminar.git.mount mnt-data-data.mount mnt-data-db.mount
  - systemctl start mnt-data-seminar.git.mount mnt-data-data.mount mnt-data-db.mount
  - systemctl enable ksi-backend.service
  - systemctl start ksi-backend.service
EOF

    cat > "$VM_DIR/meta-data" <<EOF
instance-id: ksi-backend-$(date +%s)
EOF

    cd "$VM_DIR"
    cloud-localds seed.iso user-data meta-data
    rm -f user-data meta-data
    cd - > /dev/null
fi

echo "=== VM setup complete ==="
echo "Image location: $IMAGE"
echo "Seed image location: $SEED_IMAGE"
echo ""
echo "To start the VM, run:"
echo "  .qemu/qemu-start.sh"
