#!/bin/bash
cd "$(realpath "$(dirname "$0")")/.." || { echo "ERR: Cannot cd to script dir"; exit 1; }

DIR_BE="/opt/web-backend"

if [ "$SEMINAR_GIT_URL" == "::local::" ]; then
  SEMINAR_GIT_URL=""
fi

bindfs /etc /opt/etc || { echo "ERR: Bind mount for isolate"; exit 1; }
bindfs /opt/data "$DIR_BE/data" -u ksi -g ksi -o nonempty --create-for-user=1000 || { echo "ERR: Bind mount for data"; exit 1; }
bindfs /opt/database /var/ksi-be/ -u ksi -g ksi --create-for-user=1000 || { echo "ERR: Bind mount for database dir"; exit 1; }
if [ -z "$SEMINAR_GIT_URL" ]; then
  bindfs /opt/seminar.git /var/ksi-seminar.git/ -u ksi -g ksi --create-for-user=1000 || { echo "ERR: Bind mount for seminar dir"; exit 1; }
fi

bash init-makedirs.sh || { echo "ERR: Cannot create directories"; exit 1; }

# Copy sample config if not exists
if [ ! -f "$DIR_BE/gunicorn_cfg.py" ]; then
  echo "[*] Copying sample gunicorn config..."
  cp "$DIR_BE/gunicorn_cfg.py.example" "$DIR_BE/gunicorn_cfg.py" || { echo "ERR: Cannot copy gunicorn config"; exit 1; }
fi

# Setup git name and email if not yet set
if [ -z "$(git config --global user.name)" ]; then
  echo "[*] Setting up git user name..."
  sudo -Hu ksi git config --global user.name "ksi-backend" || { echo "ERR: Cannot set git user name"; exit 1; }
fi

# Check if git user email is set
if [ -z "$(git config --global user.email)" ]; then
  echo "[*] Setting up git user email..."
  sudo -Hu ksi git config --global user.email "ksi-backend@localhost" || { echo "ERR: Cannot set git user email"; exit 1; }
fi

# Copy module lib if directory is empty
if [ ! -d "$DIR_BE/data/module_lib" ] || [ ! "$(ls -A "$DIR_BE/data/module_lib")" ]; then
  echo "[*] Setting up module lib for the first time..."
  git clone https://github.com/fi-ksi/module_lib.git  "$DIR_BE/data/module_lib" || { echo "ERR: Cannot copy module lib"; rm -rf "$DIR_BE/data/module_lib"; exit 1; }
fi

# Create seminar repo if not exists
if [ ! -d "$DIR_BE/data/seminar" ] || [ ! "$(ls -A "$DIR_BE/data/seminar")" ]; then
  echo "[*] Setting up seminar repo for the first time..."

  if [ "$SEMINAR_GIT_URL" ]; then
    echo "[*] Cloning seminar repo as SEMINAR_GIT_URL is set ...." &&
    sudo -Hu ksi git clone "$SEMINAR_GIT_URL" "$DIR_BE/data/seminar" &&
    export SEMINAR_GIT_URL="<MASKED>" ||  # prevent leaking the URL
    { echo "ERR: Prepare first seminar"; rm -rf "$DIR_BE/data/seminar"; exit 1; }
  else
    echo "[*] Creating new seminar repo as SEMINAR_GIT_URL is NOT set ...." &&
    sudo -Hu ksi git clone https://github.com/esoadamo/seminar-template.git "$DIR_BE/data/seminar" &&
    rm -rf "$DIR_BE/data/seminar/.git" &&
    sudo -Hu ksi git config --global init.defaultBranch master &&
    sudo -Hu ksi git init --bare "/var/ksi-seminar.git/" &&
    pushd "$DIR_BE/data/seminar" &&
    sudo -Hu ksi git init . &&
    sudo -Hu ksi git remote add origin "/var/ksi-seminar.git/" &&
    sudo -Hu ksi git add . &&
    sudo -Hu ksi git status &&
    sudo -Hu ksi git commit -m "Initial commit" &&
    sudo -Hu ksi git push -u origin master &&
    popd || { echo "ERR: Prepare first seminar"; rm -rf "$DIR_BE/data/seminar"; exit 1; }
  fi
fi

# create database if not exists
DB_NEEDS_INIT="false"
if [ ! -f '/var/ksi-be/.db-init-done' ]; then
  echo "[*] Database init file does not exist, checking if init should be performed"
  DB_NEEDS_INIT="$(sudo -Hu ksi bash -c "source ksi-py3-venv/bin/activate && python -c \"import db; import model; model.Base.metadata.create_all(db.engine); print('true' if db.session.query(model.Year).first() is None else 'false')\"")" || { echo "ERR: Cannot check database init"; exit 1; }
  echo "[*] Database needs init: $DB_NEEDS_INIT"
fi

if [ "$DB_NEEDS_INIT" == "true" ]; then
  echo "[*] Database does not exist yet, creating initial database" &&
  DB_MODE="$(sudo -Hu ksi bash -c "source ksi-py3-venv/bin/activate && python -c \"import db; print(db.db_mode.value); db.session.close()\"")" &&
  echo "[*] Database mode is $DB_MODE" &&
  mv "$DIR_BE/.docker/init_dev_data.py" "$DIR_BE/init_dev_data.py" &&
  sudo -Hu ksi bash -c "source ksi-py3-venv/bin/activate && python $DIR_BE/init_dev_data.py" &&
  echo "[*] Database created, now populating with initial data" &&
  touch /var/ksi-be/.db-init-done &&
  echo "[*] Database created" || { echo "ERR: Cannot start the DB"; rm -f '/var/ksi-be/db.sqlite' &> /dev/null; exit 1; }
fi

# Start the backend
sudo -Hu ksi bash -c 'source ksi-py3-venv/bin/activate && gunicorn -c gunicorn_cfg.py app:api'
