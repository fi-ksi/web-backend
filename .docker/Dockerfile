FROM python:3.7-buster
ENV DIR_BE /opt/web-backend
# copy files
RUN mkdir $DIR_BE
WORKDIR $DIR_BE
ADD web-backend $DIR_BE/

EXPOSE 3030

# install and setup required software
RUN apt-get update \
    && apt-get install -y acl sudo \
    && wget 'https://deb.ahlava.cz/isolate-1.8.1.deb' -O isolate.deb \
    && dpkg -i isolate.deb\
    && rm isolate.deb \
    && sudo apt-get clean \
    && pip3 install virtualenv --no-cache-dir \
    && virtualenv -p python3 ksi-py3-venv \
    && ln -s /etc /opt/etc \
    && bash -c 'cd $DIR_BE  && ./init-makedirs.sh' \
    && echo 'SQL_ALCHEMY_URI = "sqlite:////var/ksi-be/db.sqlite"' > config.py \
    && sed -e 's/READ COMMITTED/SERIALIZABLE/' -i db.py \
    && sed -e 's/127.0.0.1/0.0.0.0/' -i gunicorn_cfg.py

RUN bash -c 'cd $DIR_BE && source ksi-py3-venv/bin/activate && pip install --no-cache-dir -r requirements.txt' \
    && mkdir /var/ksi-be

COPY seminar $DIR_BE/data/seminar
COPY module_lib $DIR_BE/data/module_lib

RUN useradd -Mr ksi \
    && chown ksi:ksi -R $DIR_BE/data/seminar/

ENTRYPOINT ["/bin/bash"]
CMD ["./.docker/start.sh"]
