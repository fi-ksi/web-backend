#!/bin/bash

gunicorn --bind 0:3000 app:api
