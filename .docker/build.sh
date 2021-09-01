#/bin/bash
cd "$(realpath "$(dirname "$0")")/../.." &&
docker rmi -f ksi-be &>/dev/null &&
docker build -f web-backend/.docker/Dockerfile -t ksi-be . &&
if [[ "$1" == "--run" ]]; then
  ./web-backend/.docker/start.sh "$2"
fi
