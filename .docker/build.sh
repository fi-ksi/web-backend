#/bin/bash
cd "$(realpath "$(dirname "$0")")/../.." &&
docker rmi -f ksi-be &&
docker build -f web-backend/.docker/Dockerfile -t ksi-be . &&
if [[ "$1" == "--run" ]]; then
  docker stop ksi-be
  docker rm ksi-be
  docker run \
    -p 3030:3030 \
    -v "$2:/var/ksi-be/" \
    --rm \
    --device /dev/fuse \
    --cap-add=SYS_ADMIN \
    --security-opt apparmor:unconfined \
    -it \
    --name ksi-be \
    ksi-be
fi
