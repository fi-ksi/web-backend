# Backend for Online Seminar of Informatics

[ksi.fi.muni.cz](https://ksi.fi.muni.cz/)

## Running with Docker

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

You can also use MySQL database by modifying environment variables. For example, see [config.py.example](./config.py.example).

## Running with QEMU (without root access)

If you don't have root access to run Docker directly, you can run the backend in a QEMU virtual machine:

```bash
# 1. Setup VM (downloads Debian 12 image, ~5 minutes first time)
.qemu/qemu-setup.sh

# 2. Start the VM
.qemu/qemu-start.sh

# 3. Wait 2-3 minutes for provisioning, then access:
# Backend: http://localhost:3030
```

The VM automatically:
- Mounts the project directory as a shared folder
- Builds and starts the Docker container inside the VM
- Forwards port 3030 to localhost

Use `--gui` flag to see the VM display: `.qemu/qemu-start.sh --gui`

For more options (systemd service, configuration, troubleshooting), see [.qemu/README.md](.qemu/README.md).

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
