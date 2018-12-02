import hashlib
import random
import string

from db import session
import model

TOKEN_LENGTH = 40

def _generate_token():
    return ''.join([
        random.choice(string.ascii_letters + string.digits)
        for x in range(TOKEN_LENGTH)
    ])


def new_token():
    return hashlib.sha256(_generate_token().encode('utf-8')).hexdigest()[:TOKEN_LENGTH]


def get(user_id):
    return normalize(session.query(model.UserNotify).get(user_id), user_id)


def normalize(notify, user_id):
    if notify is None:
        notify = model.UserNotify(
            user=user_id,
            notify_eval=True,
            notify_response=True,
            notify_ksi=True,
            notify_events=True,
        )
    return notify
