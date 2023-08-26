#!/bin/bash
cd "$(realpath "$(dirname "$0")")/.." &&
# docker rmi -f ksi-be &>/dev/null &&
docker build --no-cache -f .docker/Dockerfile -t ksi-be . &&
if [[ "$1" == "--run" ]]; then
  ./.docker/start.sh "$2" "$3" "$4"
fi
