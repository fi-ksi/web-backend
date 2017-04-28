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

* `./runner start`

  Log je v `/var/log/gunicorn/`.

## `config.py`
Pro funnkcnost backendu musi byt v korenove slozce repozitare souboor `config.py` s heslem k databazi ve formatu:

	SQL_ALCHEMY_URI = 'mysql://username:password@server/db_name?charset=utf8'

## Prvni spusteni

Pro vytvoreni tabulek spustit pouze s jednim workerem a odkomentovat prislusny
kud kodu v `app.py`.

## Ocekavana struktura dat v systemu

* any-dir/any-dir/.../any-dir
  * `pypy`
  * any-dir-with-backend


