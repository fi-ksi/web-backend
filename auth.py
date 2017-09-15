import bcrypt
import random
import string

from db import session
import model
import datetime

TOKEN_LENGTH = 40


def _generate_token():
    return ''.join([
        random.choice(string.ascii_letters + string.digits)
        for x in range(TOKEN_LENGTH)
    ])


class Error:
    INVALID_REQUEST = 'invalid_request'
    UNAUTHORIZED_CLIENT = 'unauthorized_client'


class GrantType:
    CODE = 'password'
    CODE = 'refresh_token'


def get_hashed_password(plain_text_password):
    return bcrypt.hashpw(plain_text_password.encode('utf-8'), bcrypt.gensalt())


def check_password(plain_text_password, hashed_password):
    return bcrypt.checkpw(plain_text_password.encode('utf-8'),
                          hashed_password.encode('utf-8'))


class OAuth2Token(object):
    def __init__(self, client_id):
        self.value = _generate_token()
        self.expire = datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        self.kind = 'Bearer'
        self.refresh = _generate_token()

        token = model.Token()
        token.access_token = self.value
        token.expire = self.expire
        token.refresh_token = self.refresh
        token.user = client_id

        try:
            session.add(token)
            session.commit()
        except:
            session.rollback()
            raise

    @property
    def data(self):
        return {
            'access_token': self.value,
            'token_type': self.kind,
            'expires_in': int((self.expire-datetime.datetime.utcnow()).
                              total_seconds()),
            'refresh_token': self.refresh
        }
