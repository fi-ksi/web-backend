import bcrypt
import secrets

from db import session
import model
import datetime

TOKEN_LENGTH = 40


def _generate_token():
    return secrets.token_urlsafe(TOKEN_LENGTH)


def get_hashed_password(plain_text_password: str) -> str:
    return bcrypt.hashpw(plain_text_password.encode('utf-8'), bcrypt.gensalt()).decode('ascii')


def check_password(plain_text_password: str, hashed_password: str) -> bool:
    plain_bytes = plain_text_password.encode('utf8')
    hash_bytes = hashed_password.encode('utf8')

    return bcrypt.checkpw(plain_bytes, hash_bytes)


class OAuth2Token(object):
    def __init__(self, client_id: model.User):
        self.value = _generate_token()
        self.expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=1)
        self.kind = 'Bearer'
        self.refresh = _generate_token()

        token = model.Token()
        token.access_token = self.value
        token.expire = self.expire
        token.refresh_token = self.refresh
        token.user = client_id.id

        try:
            client_id.last_logged_in = datetime.datetime.utcnow()
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
