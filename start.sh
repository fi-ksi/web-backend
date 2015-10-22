#!/bin/bash

gunicorn -c gunicorn_cfg.py --certfile=../cert/servercert.pem --keyfile=../cert/np_serverkey.pem --ca-certs=../cert/terenacert.pem app:api
