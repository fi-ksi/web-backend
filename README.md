# Backend for Online Seminar of Informatics

[ksi.fi.muni.cz](https://ksi.fi.muni.cz/)

## Running with docker

The backend can be run inside a docker container for testing purposes. To build the image, run:

```bash
docker compose up --build
```

This will build the image and start the container, together with development versions of the frontend.
- backend will be running at [http://localhost:3030](http://localhost:3030)
- frontend will be running at [http://localhost:4201](http://localhost:4201)
- old frontend will be running at [http://localhost:8080](http://localhost:8080)

The master account is `admin@localhost` with password `change-me`.

The backend is created together with a sample [seminar repository](https://github.com/fi-ksi/seminar-template).
To use the repository, you must clone it locally after starting the container:

```bash
git clone .docker/data/seminar.git seminar-dev
```

The backend will automatically push and pull from the repository in the container, you can work with your own clone.

### Using MySQL database with docker

To use MySQL database instead of SQLite, you need to change the `DB_URL` environment variable in the `config.py` file and 
then mount the file into the container. This can be done by uncommenting following line in `docker-compose.yml`:

```yaml
    volumes:
      - ./config.py:/opt/web-backend/config.py # Uncomment to use custom config.py (e.g. for MySQL database instead of SQLite)
```

## Running manually

Running manually is discouraged, as it requires a lot of setup. If you still want to run the backend manually, follow the instructions below.

### Software needed

 * Python 3.7+
 * virtualenv
 * packages from `requirements.txt`
 * [isolate](https://github.com/ioi/isolate)

### Installation

 1. Clone this repository.
 2. Run `init-makedirs.sh`.
 3. Install virtualenv & packages into `ksi-py3-venv` directory.
    ```
    virtualenv -p python3 ksi-py3-venv
    source ksi-py3-venv/bin/activate
    pip3 install -r requirements.txt
    ```
 4. Enter db url into `config.py` file. Format is the same as specified in `config.py.dist`
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

### Server control

 * To start server run: `./runner start`.
 * To stop server run: `./runner stop`.
 * The `runner` script must be executed in server`s root directory.
 * Logs are stored in `/var/log/gunicorn/*`.
