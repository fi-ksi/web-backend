#!/bin/bash

DIR_DB="$1"
DIR_SEMINAR="$2"
DIR_MODULE_LIB="$3"

[ -z "$DIR_DB" -o ! -d "$DIR_DB" ] && { echo "ERR: Given DB path is invalid"; exit 1; }
[ -z "$DIR_SEMINAR" -o ! -d "$DIR_SEMINAR" ] && { echo "ERR: Given seminar repo path is invalid"; exit 1; }
[ -z "$DIR_MODULE_LIB" -o ! -d "$DIR_MODULE_LIB" ] && { echo "ERR: Given module lib path is invalid"; exit 1; }

echo "Selected options are"
echo "- DB: $DIR_DB"
echo "- SEMINAR: $DIR_SEMINAR"
echo "- MODULE: $DIR_MODULE_LIB"

docker stop ksi-be &>/dev/null
docker rm ksi-be &>/dev/null
docker run \
  -p 3030:3030 \
  -v "$DIR_DB:/var/ksi-be/" \
  -v "$DIR_SEMINAR:/var/ksi-seminar/" \
  -v "$DIR_MODULE_LIB:/var/ksi-module-lib/" \
  --device /dev/fuse \
  --cap-add=SYS_ADMIN \
  --security-opt apparmor:unconfined \
  -it \
  --name ksi-be \
  ksi-be
