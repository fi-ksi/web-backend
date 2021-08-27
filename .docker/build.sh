#/bin/bash
cd "$(realpath "$(dirname "$0")")/../.." &&
docker rmi -f ksi-be &&
docker build -f web-backend/.docker/Dockerfile -t ksi-be . &&
if [[ "$1" == "--run" ]]; then
   docker run -p 3030:3030 -v "$2:/var/ksi-be/" -it ksi-be
fi
