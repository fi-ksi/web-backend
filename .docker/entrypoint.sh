#!/bin/bash
cd "$(realpath "$(dirname "$0")")/.." || { echo "ERR: Cannot cd to script dir"; exit 1; }

DIR_BE="/opt/web-backend"

bindfs /etc /opt/etc || { echo "ERR: Bind mount for isolate"; exit 1; }
bindfs /var/ksi-seminar "$DIR_BE/data/seminar" -u ksi -g ksi || { echo "ERR: Bind mount for seminar repo"; exit 1; }
bindfs /var/ksi-module-lib "$DIR_BE/data/module_lib" -u ksi -g ksi -r || { echo "ERR: Bind mount for module lib"; exit 1; }

# create database if not exists
if [ ! -f '/var/ksi-be/db.sqlite' ]; then
  echo "Database does not exist yet, creating all tables" &&
  cp app.py gen-db.py &&
  sed -e 's/# model/model/' -i gen-db.py &&
  echo 'session.add(model.Year(year="initial year", sealed=False, point_pad=0)); session.commit()' >> gen-db.py &&
  sudo -Hu ksi bash -c 'source ksi-py3-venv/bin/activate && python gen-db.py' &&
  rm gen-db.py &&
  echo "Database created" || { echo "ERR: Cannot start the DB"; exit 1; }
fi

# start the server
sudo -Hu ksi bash -c 'source ksi-py3-venv/bin/activate && gunicorn -c gunicorn_cfg.py app:api'
