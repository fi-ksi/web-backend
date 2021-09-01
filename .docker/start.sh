#!/bin/bash

DIR_DB="$1"

[ ! -d "$DIR_DB" ] && { echo "ERR: Given DB path is invalid"; exit 1; }

docker stop ksi-be &>/dev/null
docker rm ksi-be &>/dev/null
docker run \
  -p 3030:3030 \
  -v "$1:/var/ksi-be/" \
  --rm \
  --device /dev/fuse \
  --cap-add=SYS_ADMIN \
  --security-opt apparmor:unconfined \
  -it \
  --name ksi-be \
  ksi-be