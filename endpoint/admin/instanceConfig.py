import json

import falcon

from sqlalchemy.exc import SQLAlchemyError

import util.config
from db import session
from util.logger import audit_log


class InstanceConfig:
    def on_post(self, req, resp):
        try:
            userinfo = req.context['user']

            if not userinfo.is_logged_in() or not userinfo.is_admin():
                resp.status = falcon.HTTP_401
                req.context['result'] = {
                    'result': 'error',
                    'error': 'Only admin can change the instance configuration.'
                }
                return

            data = json.loads(req.stream.read().decode('utf-8'))
            key = data['key']
            value = data['value']

            if key is None or value is None:
                resp.status = falcon.HTTP_400
                req.context['result'] = {
                    'result': 'error',
                    'error': 'Missing key or value.'
                }
                return

            audit_log(
                scope="CONFIG",
                user_id=userinfo.id,
                message=f"Changed instance config {key}",
                message_meta={"key": key, "value": value}
            )
            util.config.set_config(key, value)
            req.context['result'] = {}
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()

    def on_get(self, req, resp):
        try:
            userinfo = req.context['user']

            if not userinfo.is_logged_in() or not userinfo.is_admin():
                resp.status = falcon.HTTP_401
                req.context['result'] = {
                    'result': 'error',
                    'error': 'Only admin can see the instance configuration.'
                }
                return

            req.context['result'] = {'config': list(util.config.get_all(include_secret=False).values())}
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()
