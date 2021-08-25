#!/bin/bash
cd "$(realpath "$(dirname "$0")")/.."

# create database if not exists
if [ ! -f '/var/ksi-be/db.sqlite' ]; then
  echo "Database does not exist yet, creating all tables" &&
  cp app.py gen-db.py &&
  sed -e 's/# model/model/' -i gen-db.py &&
  echo 'session.add(model.Year(year="initial year", sealed=False, point_pad=0)); session.commit()' >> gen-db.py &&
  sudo -Hu ksi bash -c 'source ksi-py3-venv/bin/activate && python gen-db.py' &&
  rm gen-db.py &&
  echo "Database created"
fi

# start the server
sudo -Hu ksi bash -c 'source ksi-py3-venv/bin/activate && gunicorn -c gunicorn_cfg.py app:api'
