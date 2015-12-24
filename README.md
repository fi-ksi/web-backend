# Backend pro KSI web

## Potrebny software

* Python 3.5 (3.4 pravdepodobne postaci)

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

## Spusteni

* HTTP: `gunicorn --bind 127.0.0.1:3000 app:api`
* HTTPS: `gunicorn --bind 127.0.0.1:3000 --certfile=server.crt --keyfile=key.pem app:api`

Modifikaci parametru `--bind` lze zmenit cilovou IP adresu a port (format: `<ip>:<port>`). Pro spusteni na vsech dostupnych IP adresach, staci nastavit `--bind` na format `0:<port>`.

Doporucene spusteni: skriptem ./start.sh, zabiti serveru skriptem ./kill.sh.

## Testovani auth

* dojit na http://server:port/debug - dojde k vytvoreni uzivatele 'user' s heslem '1234'
* http://server:port/profile - pri spravnem basic auth (base64 user:password v Authenticate headeru HTTP requestu) is_logged vraci true

## Mergovani vetve `dev` do vetve `master`

Pri merge `dev` do `master` je nutne zachovat konfiguracni soubory jednotlivych vetvi, proto mergujte takto:

	git checkout master
	git merge --no-commit dev
	git reset HEAD <config_file>
	git checkout -- <config_file>
	git commit -m "Merged dev to master"

You can put lines 3 & 4 in a for loop if you have a list of files to skip.

Pokud naleznete hezci reseni, budu rad...

## `config.py`
Pro funnkcnost backendu musi byt v korenove slozece repozitare souboor `config.py` s heslem k databazi ve formatu:

	SQL_ALCHEMY_URI = 'mysql://ksi:4R98HgIufjDnC9wnn89@127.0.0.1/ksi_prod?charset=utf8'

