# Backend pro KSI web

## Potrebny software

* Python 3.5 (3.4 pravdepodobne postaci)

### Python balicky

Je vhodne vyuzit virtualenv - pip install virtualenv, virtualenv env, source env/bin/activate. Timto je zajisteno nepospineni systemove instalace.

* falcon (0.3.0)
* gunicorn (19.3.0)
* talons (0.3)
* SQLAlchemy (1.0.8) 

## Spusteni

* cd do adresare s app.py
* gunicorn app:api

A backend pobezi na 127.0.0.1:8000. Je mozno predat gunicornu --bind parametr (napr. gunicorn --bind 0:8000 app:api) pro bind na jinou adresu.

## Testovani auth

* dojit na http://server:port/debug - dojde k vytvoreni uzivatele 'user' s heslem '1234'
* http://server:port/profile - pri spravnem basic auth (base64 user:password v Authenticate headeru HTTP requestu) is_logged vraci true 
