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


class AuthorizationError:
    INVALID_REQUEST = 'invalid_request'
    UNAUTHORIZED_CLIENT = 'unauthorized_client'
    ACCESS_DENIED = 'access_denied'
    UNSUPPORTED_RESPONSE_TYPE = 'unsupported_response_type'
    INVALID_SCOPE = 'invalid_scope'
    SERVER_ERROR = 'server_error'
    TEMPORARILY_UNAVAILABLE = 'temporarily_unavailable'


class ResponseType:
    CODE = 'code'


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


class Provider(object):

    def _valid_client_id(self, client_id):
        return session.query(model.User).get(client_id)

    def _authorize(self):
        return self.OAuth2Token().data

    def authorization_request(self, req, resp):
        def success(uri, code):
            query_params = urllib.parse.parse_qs(uri.query)
            query_params['code'] = code

            return query_params

        def failure(uri, error):
            query_params = urllib.parse.parse_qs(uri.query)
            query_params['error'] = error

            return query_params

        response_type, client_id, redirect_uri = (
            req.get_param('response_type'),
            req.get_param('client_id'),
            req.get_param('redirect_uri'))

        uri = urllib.parse.urlparse(redirect_uri)

        if not any((response_type, client_id, redirect_uri)):
            failure(uri, AuthorizationError.INVALID_REQUEST)

        if response_type != ResponseType.CODE:
            failure(uri, AuthorizationError.UNSUPPORTED_RESPONSE_TYPE)

        code = _generate_token()

        query_params = success(uri, code)
        resp.location = urllib.parse.urlunparse(
            (uri.scheme,
             uri.netloc,
             uri.path,
             uri.params,
             urllib.parse.urlencode(query_params),
             uri.fragment))
        resp.status = falcon.HTTP_302

    def access_token_request(self, req, resp):
        response_type, client_id, redirect_uri = (
            req.get_param('response_type'),
            req.get_param('client_id'),
            req.get_param('redirect_uri'))

        req.context['result'] = OAuth2Token().data
        resp.status = falcon.HTTP_200

    def authorization_request(self, req, resp):
