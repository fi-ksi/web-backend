import string
import random
import urllib

import falcon

from db import session
import model

TOKEN_LENGTH = 40


def _generate_token():
    return ''.join([random.choice((string.ascii_letters +
                                   string.digits)) for
                    x in range(TOKEN_LENGTH)])


class Error:
    INVALID_REQUEST = 'invalid_request'
    UNAUTHORIZED_CLIENT = 'unauthorized_client'


class GrantType:
    CODE = 'password'


class OAuth2Token(object):
    def __init__(self, client_id):
        self.value = _generate_token()
        self.expire = 3600
        self.kind = 'Bearer'
        self.refresh = _generate_token()

        token = model.Token()
        token.access = self.value
        token.expire = self.expire
        token.refresh = self.expire
        token.id_user = client_id

        session.add(token)
        session.commit()

    @property
    def data(self):
        return {
            'access_token': self.value,
            'token_type': self.kind,
            'expires_in': self.expire,
            'refresh_token': self.refresh
        }


class Provider(object):

    def request_access_token(self, req, resp):
        grant_type, username, password = (
            req.get_param('grant_type'),
            req.get_param('username'),
            req.get_param('password'))

        challenge = session.query(model.User).filter(
            model.User.name_nick == username,
            model.User.password == password).first()

        if challenge:
            req.context['result'] = OAuth2Token(challenge.id).data
            resp.status = falcon.HTTP_200
        else:
            req.context['result'] = {'error': Error.UNAUTHORIZED_CLIENT}
            resp.status = falcon.HTTP_400

