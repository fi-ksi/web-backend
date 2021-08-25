#/bin/bash
cd "$(realpath "$(dirname "$0")")/../.." &&
docker build -f web-backend/.docker/Dockerfile -t ksi-be .
