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
                req.context['result'] = 'Chyba 403: špatný autorizační token!'
                resp.status = falcon.HTTP_403
                return

            valid_types = ['eval', 'response', 'ksi', 'events', 'all']
            u_type = req.get_param('type')

            if u_type not in valid_types:
                req.context['result'] = 'Chyba 400: neplatný typ zprávy!'
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
            req.context['result'] = 'Úspěšně odhlášeno.'

        except SQLAlchemyError:
            req.context['result'] = 'Chyba 500: nastala výjimka, kontaktuj orga!'
            session.rollback()
            raise
        finally:
            session.close()
