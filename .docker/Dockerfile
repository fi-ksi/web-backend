FROM python:3.11-bookworm
ENV DIR_BE /opt/web-backend

RUN mkdir $DIR_BE
WORKDIR $DIR_BE
EXPOSE 3030

# install and setup required software
RUN wget -O - https://deb.adamhlavacek.com/pub.gpg | apt-key add - \
    && echo "deb https://deb.adamhlavacek.com ./" >> /etc/apt/sources.list \
    && apt-get update \
    && apt-get install -y pandoc acl sudo curl isolate bindfs libpython3.7 libcap2 sqlite3 python3-distutils \
    && sudo apt-get clean \
    && pip3 install virtualenv --no-cache-dir \
    && virtualenv -p python3 ksi-py3-venv \
    && mkdir /opt/etc \
    && echo 'SQL_ALCHEMY_URI = "sqlite:////var/ksi-be/db.sqlite"' > config.py \
    && echo 'ENCRYPTION_KEY = "AGE-SECRET-KEY-1TLU9YP9V55UDN4LE9Q0QYDH6ZXDA2JWRCZTHQTWPTYV7U800PFFS3PDNS9"' >> config.py

ADD requirements.txt $DIR_BE/requirements.txt
RUN bash -c 'cd $DIR_BE && source ksi-py3-venv/bin/activate && pip install --no-cache-dir -r requirements.txt'

ADD . $DIR_BE/

RUN bash -c 'cd $DIR_BE  && ./init-makedirs.sh' \
    && bash -c 'cd $DIR_BE  && chmod +x .docker/entrypoint.sh' \
    && mkdir /var/ksi-be.ro \
    && mkdir /var/ksi-be \
    && mkdir /var/ksi-seminar.git \
    && mv "$DIR_BE/.docker/config_isolate" /usr/local/etc/isolate \
    && chmod 644 /usr/local/etc/isolate \
    && chmod u+s /usr/bin/isolate \
    && chown root:root /usr/local/etc/isolate \
    && sed -e 's/127.0.0.1/0.0.0.0/' -i gunicorn_cfg.py.example

RUN useradd -mru 999 ksi

HEALTHCHECK --interval=300s --start-period=180s CMD curl --silent --fail http://127.0.0.1:3030/years || exit 1
ENTRYPOINT ["/bin/bash"]
CMD ["./.docker/entrypoint.sh"]
