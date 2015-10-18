#!/bin/bash

kill $@ `cat gunicorn_pid`
