import json
import falcon
from sqlalchemy.exc import SQLAlchemyError

from db import session
import model
import util


class Unsubscribe(object):

    def on_get(self, req, resp, id):
        return self.on_post(req, resp, id)

    def on_post(self, req, resp, id):
        """
        Params:
            - ?token=auth_token
            - ?type=eval|response|ksi|events|all
        """
        try:
            resp.content_type = 'text/html; charset=utf-8'

            notify = util.user_notify.get(id)
            if req.get_param('token') != notify.auth_token:
                resp.body = 'Chyba 403: špatný autorizační token!'
                resp.status = falcon.HTTP_403
                return

            valid_types = ['eval', 'response', 'ksi', 'events', 'all']
            u_type = req.get_param('type')

            if u_type not in valid_types:
                resp.body = 'Chyba 400: neplatný typ zprávy!'
                resp.status = falcon.HTTP_400
                return

            if u_type == 'eval':
                notify.notify_eval = False
            elif u_type == 'response':
                notify.notify_response = False
            elif u_type == 'ksi':
                notify.notify_ksi = False
            elif u_type == 'events':
                notify.notify_events = False
            elif u_type == 'all':
                notify.notify_eval = False
                notify.notify_response = False
                notify.notify_ksi = False
                notify.notify_events = False

            session.commit()
            resp.body = 'Úspěšně odhlášeno.'

            resp.body += '<br><br>Aktuální stav notifikací pro adresu: %s:' % (
                session.query(model.User).get(id).email
            )
            resp.body += '<ul>'
            resp.body += '<li>Notifikovat o opravení mého řešení: %s.</li>' % (
                'ano' if notify.notify_eval else 'ne'
            )
            resp.body += '<li>Notifikovat o reakci na můj komentář: %s.</li>' % (
                'ano' if notify.notify_response else 'ne'
            )
            resp.body += '<li>Notifikovat o průběhu semináře (vydání nové vlny, ...): %s.</li>' % (
                'ano' if notify.notify_ksi else 'ne'
            )
            resp.body += '<li>Zasílat pozvánky na spřátelené akce (InterLoS, InterSoB, ...): %s.</li>' % (
                'ano' if notify.notify_events else 'ne'
            )
            resp.body += '</ul>'
            resp.body += 'Další změny je možné provést v nastavení tvého profilu na webu Naskoč na FI.'

        except SQLAlchemyError:
            resp.body = 'Chyba 500: nastala výjimka, kontaktuj orga!'
            session.rollback()
            raise
        finally:
            session.close()
