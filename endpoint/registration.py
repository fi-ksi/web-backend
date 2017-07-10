# -*- coding: utf-8 -*-

import json, falcon

from db import session
from sqlalchemy.exc import SQLAlchemyError
import model
import auth
import util

class Registration(object):

    def on_post(self, req, resp):
        data = json.loads(req.stream.read().decode('utf-8'))

        try:
            existing_user = session.query(model.User).filter(model.User.email == data['email']).first()
            if existing_user != None:
                req.context['result'] = { 'error': "duplicate_user" }
                return
        except SQLAlchemyError:
            session.rollback()
            raise

        try:
            if not 'nick_name' in data: data['nick_name'] = ""
            user = model.User(email=data['email'], password=auth.get_hashed_password(data['password']), first_name=data['first_name'], last_name=data['last_name'], nick_name=data['nick_name'], sex=data['gender'], short_info=data["short_info"])
            session.add(user)
            session.commit()
        except:
            session.rollback()
            req.context['result'] = { 'error': "Nelze vytvořit uživatele, kontaktuj prosím orga." }
            raise

        try:
            profile = model.Profile(user_id=user.id, addr_street=data['addr_street'], addr_city=data['addr_city'], addr_zip=data['addr_zip'], addr_country=data['addr_country'],\
                school_name=data['school_name'], school_street=data['school_street'], school_city=data['school_city'], school_zip=data['school_zip'], school_country=data['school_country'], school_finish=int(data['school_finish']),\
                tshirt_size=data['tshirt_size'].upper())
        except:
            session.delete(user)
            req.context['result'] = { 'error': "Nelze vytvořit profil, kontaktuj prosím orga." }
            raise

        try:
            session.add(profile)
            session.commit()
        except:
            session.rollback()
            raise

        try:
            util.mail.send(user.email, '[KSI-WEB] Potvrzení registrace do Korespondenčního semináře z informatiky', 'Ahoj!<br/>Vítáme tě v Korespondenčním semináři z informatiky Fakulty informatiky Masarykovy univerzity. Nyní můžeš začít řešit naplno. Stačí se přihlásit na https://ksi.fi.muni.cz pomocí e-mailu a zvoleného hesla. Přejeme ti hodně úspěchů při řešení semináře!<br/><br/>KSI')
        except:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_traceback, file=sys.stderr)

        session.close()

