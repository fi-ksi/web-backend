#!/bin/bash

gunicorn --bind 0:4242 app:api
