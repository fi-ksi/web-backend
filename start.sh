#!/bin/bash

gunicorn -c gunicorn_cfg.py app:api
