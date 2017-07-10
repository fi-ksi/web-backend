# Backend pro KSI web

## Potřebný software

 * Python 3.5
 * virtualenv
 * balíčky viz `requirements.txt`

## První instalace

 1. Naklonovat repo.
 2. Spustit `init-makedirs.sh`, který vytvoří potřebné adresáře v kořenu
    projektu.
 3. Do adresáře `ksi-py3-venv` nainstalovat virtualenv s balíčky z
    `requirements.txt`
 4. Naplnit soubor `config.py` přístupovými údaji k databázi:

	SQL_ALCHEMY_URI = 'mysql://username:password@server/db_name?charset=utf8'

 5. Odkomentovat kód v `app.py`, který vytvoří tabulky v databázi.
 6. Spustit server, vytvoří se tabulky, kód vytvořující tabulky opět
    zakomentovat.

TODO: pypy

