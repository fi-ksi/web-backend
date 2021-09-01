FROM python:3.7-buster
ENV DIR_BE /opt/web-backend

RUN mkdir $DIR_BE
WORKDIR $DIR_BE
EXPOSE 3030

# install and setup required software
RUN wget -O - https://deb.adamhlavacek.com/pub.gpg | apt-key add - \
    && echo "deb https://deb.adamhlavacek.com ./" >> /etc/apt/sources.list \
    && apt-get update \
    && apt-get install -y acl sudo isolate bindfs \
    && sudo apt-get clean \
    && pip3 install virtualenv --no-cache-dir \
    && virtualenv -p python3 ksi-py3-venv \
    && mkdir /opt/etc \
    && echo 'SQL_ALCHEMY_URI = "sqlite:////var/ksi-be/db.sqlite"' > config.py

ADD web-backend $DIR_BE/

RUN bash -c 'cd $DIR_BE && source ksi-py3-venv/bin/activate && pip install --no-cache-dir -r requirements.txt' \
    && bash -c 'cd $DIR_BE  && ./init-makedirs.sh' \
    && bash -c 'cd $DIR_BE  && chmod +x .docker/entrypoint.sh' \
    && mkdir /var/ksi-be \
    && sed -e 's/READ COMMITTED/SERIALIZABLE/' -i db.py \
    && sed -e 's/127.0.0.1/0.0.0.0/' -i gunicorn_cfg.py

COPY seminar $DIR_BE/data/seminar
COPY module_lib $DIR_BE/data/module_lib

RUN useradd -Mr ksi \
    && chown ksi:ksi -R $DIR_BE/data/seminar/

ENTRYPOINT ["/bin/bash"]
CMD ["./.docker/entrypoint.sh"]
