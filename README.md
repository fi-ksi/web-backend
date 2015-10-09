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

## Spusteni

* HTTP: `gunicorn --bind 127.0.0.1:3000 app:api`
* HTTPS: `gunicorn --bind 127.0.0.1:3000 --certfile=server.crt --keyfile=key.pem app:api`

Modifikaci parametru `--bind` lze zmenit cilovou IP adresu a port (format: `<ip>:<port>`). Pro spusteni na vsech dostupnych IP adresach, staci nastavit `--bind` na format `0:<port>`.

## Testovani auth

* dojit na http://server:port/debug - dojde k vytvoreni uzivatele 'user' s heslem '1234'
* http://server:port/profile - pri spravnem basic auth (base64 user:password v Authenticate headeru HTTP requestu) is_logged vraci true
