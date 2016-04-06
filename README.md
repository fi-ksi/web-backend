# Backend pro KSI web

## Potrebny software

* Python 2.7

### Python balicky

Je vhodne vyuzit virtualenv - pip install virtualenv, virtualenv env, source env/bin/activate. Timto je zajisteno nepospineni systemove instalace.

* falcon (0.3.0)
* gunicorn (19.3.0)
* talons (0.3)
* SQLAlchemy (1.0.8)
* python-magic
* py-bcrypt
* PyPy (build vlozit do ~/pypy/, [how-to](http://doc.pypy.org/en/latest/build.html))
* python-dateutil
* lockfile
* pypandoc
* pyparsing
* gitpython
* humanfriendly

## Spusteni

* HTTP: `gunicorn --bind 127.0.0.1:3000 app:api`
* HTTPS: `gunicorn --bind 127.0.0.1:3000 --certfile=server.crt --keyfile=key.pem app:api`

Modifikaci parametru `--bind` lze zmenit cilovou IP adresu a port (format: `<ip>:<port>`). Pro spusteni na vsech dostupnych IP adresach, staci nastavit `--bind` na format `0:<port>`.

Doporucene spusteni: skriptem ./start.sh, zabiti serveru skriptem ./kill.sh.

## `config.py`
Pro funnkcnost backendu musi byt v korenove slozce repozitare souboor `config.py` s heslem k databazi ve formatu:

	SQL_ALCHEMY_URI = 'mysql://username:password@server/db_name?charset=utf8'

