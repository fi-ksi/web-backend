import random
import string

from db import session
import model

TOKEN_LENGTH = 40


def _generate_token():
    return ''.join([random.choice((string.ascii_letters +
                                   string.digits)) for
                    x in range(TOKEN_LENGTH)])


class OAuth2Token(object):
    def __init__(self):
        self.value = _generate_token()
        self.expire = 3600
        self.kind = 'Bearer'
        self.refresh = _generate_token()

    @property
    def data(self):
        return {
            'access_token': self.value,
            'token_type': self.kind,
            'expires_in': self.expire,
            'refresh_token': self.refresh
        }


class AuthorizationProvider(object):
    def _validate_client_id(self, client_id):
        return session.query(model.User).get(client_id)

    def _generate_authorization_code(self):
        return _generate_token()

    def authorize(self):
        return OAuth2Token().data


class Auth(object):
    provider = AuthorizationProvider()

    def on_get(self, req, resp):
        client_id, redirect_uri = (
            int(req.get_param('client_id')), req.get_param('redirect_uri'))

        resp.location = redirect_uri
        resp.set_header('code', self.provider.validate_client_id(client_id))
        resp.set_header('code', client_id)


class Token(object):
    provider = AuthorizationProvider()

    def on_post(self, req, resp):
        # client_id, code = req.get_header('client_id'), req.get_header('code')

        req.context['result'] = self.provider.authorize()
