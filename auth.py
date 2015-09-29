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
    CODE = 'refresh_token'


class OAuth2Token(object):
    def __init__(self, client_id):
        self.value = _generate_token()
        self.expire = 30
        self.kind = 'Bearer'
        self.refresh = _generate_token()

        token = model.Token()
        token.access_token = self.value
        token.expire = self.expire
        token.refresh_token = self.refresh
        token.user = client_id

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
