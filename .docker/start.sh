#!/bin/bash

DIR_DB="$1"
DIR_DATA="$2"
DIR_MODULE_LIB="$3"

[ -z "$DIR_DB" -o ! -d "$DIR_DB" ] && { echo "ERR: Given DB path is invalid"; exit 1; }
[ -z "$DIR_DATA" -o ! -d "$DIR_DATA" ] && { echo "ERR: Given data path is invalid"; exit 1; }

echo "Selected options are"
echo "- DB: $DIR_DB"
echo "- DATA: $DIR_DATA"

docker stop ksi-be &>/dev/null
docker rm ksi-be &>/dev/null
docker run \
  -p 3030:3030 \
  -v "$DIR_DB:/var/ksi-be.ro/" \
  -v "$DIR_DATA:/var/ksi-data.ro/" \
  --device /dev/fuse \
  --cap-add=SYS_ADMIN \
  --privileged=true \
  --security-opt apparmor:unconfined \
  -it \
  --name ksi-be \
  ksi-be
