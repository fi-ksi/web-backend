# Backend for KSI web

[https://ksi.fi.muni.cz](https://ksi.fi.muni.cz/)

## Software needed

 * Python 3.5
 * virtualenv
 * packages from `requirements.txt`
 * [isolate](https://github.com/ioi/isolate)

## Installation

 1. Clone this repository.
 2. Run `init-makedirs.sh`.
 3. Install virtualenv & packages into `ksi-py3-venv` directory.
    ```
    virtualenv -p python3 ksi-py3-venv
    source ksi-py3-venv/bin/activate
    pip3 install -r requirements.txt
    ```
 4. Enter db url into `config.py` file. Format:
    ```
    SQL_ALCHEMY_URI = 'mysql://username:password@server/db_name?charset=utf8mb4'
    ```

 5. Uncomment part of the `app.py`, which creates database structure.
 6. Run the server, comment the database-create-section in `run.py`
 7. Install `isolate` with box directory `/tmp/box`.
 8. Bind-mount `/etc` directory to `/opt/etc` (this is required for sandbox to
    work):
     ```
     $ mount --bind /etc /opt/etc
     ```
    Do not forget to add it to `/etc/fstab`.
 9. Optional: make `/tmp` tmpfs.
 10. Optional: ensure the server will be started after system boots up
     (run `./runner start`).

## Server control

 * To start server run: `./runner start`.
 * To stop server run: `./runner stop`.
 * The `runner` script must be executed in server`s root directory.
 * Logs are stored in `/var/log/gunicorn/*`.
