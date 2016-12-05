# -*- coding: utf-8 -*-

import falcon

from sqlalchemy.exc import SQLAlchemyError
from db import session
import auth
import model
import util

class Error:
    INVALID_REQUEST = 'invalid_request'
    UNAUTHORIZED_CLIENT = 'unauthorized_client'

class Authorize(object):

    def _auth(self, req, resp):
        username = req.get_param('username')
        password = req.get_param('password')

        try:
            challenge = session.query(model.User).filter(
                model.User.email == username, model.User.enabled).first()

            if username and password and challenge and auth.check_password(password, challenge.password):
                req.context['result'] = auth.OAuth2Token(challenge.id).data
            else:
                req.context['result'] = {'error': Error.UNAUTHORIZED_CLIENT}
                resp.status = falcon.HTTP_400
        except SQLAlchemyError:
            session.rollback()
            raise

    def _refresh(self, req, resp):
        refresh_token = req.get_param('refresh_token')

        try:
            token = session.query(model.Token).filter(
                model.Token.refresh_token == refresh_token).first()

            if token:
                session.delete(token)
                req.context['result'] = auth.OAuth2Token(token.user).data
            else:
                req.context['result'] = {'error': Error.UNAUTHORIZED_CLIENT}
                resp.status = falcon.HTTP_400
        except SQLAlchemyError:
            session.rollback()
            raise

    def on_post(self, req, resp):
        try:
            grant_type = req.get_param('grant_type')
            util.auth.update_tokens()

            if grant_type == 'password':
                self._auth(req, resp)
            elif grant_type == 'refresh_token':
                self._refresh(req, resp)
            else:
                resp.status = falcon.HTTP_400

        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()

class Logout(object):

    def on_get(self, req, resp):
        try:
            if not req.context['user'].is_logged_in():
                return

            token = session.query(model.Token).filter(model.Token.access_token == req.context['user'].token).first()

            if not token:
                return

            session.delete(token)
            session.commit()
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()

