import hashlib
import random
import string

TOKEN_LENGTH = 40

def _generate_token():
    return ''.join([
        random.choice(string.ascii_letters + string.digits)
        for x in range(TOKEN_LENGTH)
    ])


def new_token():
    return hashlib.sha256(_generate_token().encode('utf-8')).hexdigest()[:TOKEN_LENGTH]
