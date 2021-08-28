import json
import falcon
import sys
import traceback
from sqlalchemy.exc import SQLAlchemyError

from db import session
import model
import auth
import util


class Registration(object):

    def on_post(self, req, resp):
        data = json.loads(req.stream.read().decode('utf-8'))

        try:
            existing_user = session.query(model.User).\
                filter(model.User.email == data['email']).\
                first()

            if existing_user is not None:
                req.context['result'] = {'error': "duplicate_user"}
                return
        except SQLAlchemyError:
            session.rollback()
            raise

        try:
            if 'nick_name' not in data:
                data['nick_name'] = ""
            user = model.User(
                email=data['email'],
                password=auth.get_hashed_password(data['password']),
                first_name=data['first_name'],
                last_name=data['last_name'],
                nick_name=data['nick_name'],
                sex=data['gender'],
                short_info=data["short_info"]
            )
            session.add(user)
            session.commit()
        except SQLAlchemyError:
            session.rollback()
            req.context['result'] = {
                'error': "Nelze vytvořit uživatele, kontaktuj prosím orga."
            }
            raise

        try:
            profile = model.Profile(
                user_id=user.id,
                addr_street=data['addr_street'],
                addr_city=data['addr_city'],
                addr_zip=data['addr_zip'],
                addr_country=data['addr_country'],
                school_name=data['school_name'],
                school_street=data['school_street'],
                school_city=data['school_city'],
                school_zip=data['school_zip'],
                school_country=data['school_country'],
                school_finish=int(data['school_finish']),
                tshirt_size=data['tshirt_size'].upper(),
                referral=data.get('referral', "{}")
            )
        except BaseException:
            session.delete(user)
            session.commit()
            req.context['result'] = {
                'error': "Nelze vytvořit profil, kontaktuj prosím orga."
            }
            raise

        try:
            session.add(profile)
            session.commit()
        except SQLAlchemyError:
            session.rollback()
            raise

        try:
            notify = model.UserNotify(
                user=user.id,
                auth_token=util.user_notify.new_token(),
                notify_eval=data['notify_eval'] if 'notify_eval' in data else True,
                notify_response=data['notify_response'] if 'notify_response' in data else True,
                notify_ksi=data['notify_ksi'] if 'notify_ksi' in data else True,
                notify_events=data['notify_events'] if 'notify_events' in data else True,
            )
        except BaseException:
            session.delete(profile)
            session.commit()
            session.delete(user)
            session.commit()
            req.context['result'] = {
                'error': "Nelze vytvořit notifikační záznam, kontaktuj prosím orga."
            }
            raise

        try:
            session.add(notify)
            session.commit()
        except SQLAlchemyError:
            session.rollback()
            raise

        try:
            util.mail.send(
                user.email,
                '[KSI-WEB] Potvrzení registrace do Korespondenčního semináře '
                'z informatiky', 'Ahoj!<br/>Vítáme tě v Korespondenčním '
                'semináři z informatiky Fakulty informatiky Masarykovy '
                'univerzity. Nyní můžeš začít řešit naplno. Stačí se přihlásit'
                ' na https://ksi.fi.muni.cz pomocí e-mailu a zvoleného hesla. '
                'Přejeme ti hodně úspěchů při řešení semináře!<br/><br/>KSI'
            )
        except SQLAlchemyError:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_traceback,
                                      file=sys.stderr)

        session.close()
        req.context['result'] = {}
