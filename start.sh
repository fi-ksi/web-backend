#!/bin/bash

gunicorn -c gunicorn_cfg.py --certfile=../cert/servercert.pem --keyfile=../cert/np_serverkey.pem app:api
