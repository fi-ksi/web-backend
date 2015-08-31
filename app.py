import falcon
import json

from talons.auth import middleware, interfaces
from talons.auth import basicauth, external

import model
import endpoint
from db import engine, session


class JSONTranslator(object):

    def process_request(self, req, resp):
        return

    def process_response(self, req, resp, endpoint):
        if 'result' not in req.context:
            return

        resp.body = json.dumps(req.context['result'], sort_keys=True, indent=4)


class SkipIdentifier(interfaces.Identifies):
    def identify(self, request):
        identity = interfaces.Identity(None, key=None)
        request.env[self.IDENTITY_ENV_KEY] = identity
        return True


def cors_middleware(request, response, params):
    origin = request.get_header('Origin')

    if origin in ('http://localhost:4200',):
        response.set_header('Access-Control-Allow-Origin', origin)

    response.set_header('Access-Control-Allow-Headers', 'Content-Type')
    response.set_header('Access-Control-Allow-Methods', 'OPTIONS')


def authenticate(identity):
    return True


def authorize(identity, request):
    challenge = session.query(model.User).filter(
        model.User.name_nick == identity.login,
        model.User.password == identity.key).first()
    print(identity.login)
    print(identity.key)
    print(challenge)

    if challenge:
        if challenge.admin is True:
            request.request.env['PERMISSIONS'] = 2
        else:
            request.request.env['PERMISSIONS'] = 1
    else:
        request.request.env['PERMISSIONS'] = 0

    print(request.request.env['PERMISSIONS'])

    return True


auth_middleware = middleware.create_middleware(
    identify_with=[basicauth.Identifier, SkipIdentifier],
    authenticate_with=[external.Authenticator(external_authfn=authenticate)],
    authorize_with=external.Authorizer(external_authz_callable=authorize))

api = falcon.API(before=[cors_middleware, auth_middleware],
                 middleware=[JSONTranslator()])

model.Base.metadata.create_all(engine)

api.add_route('/articles', endpoint.Articles())
api.add_route('/articles/{id}', endpoint.Article())
api.add_route('/achivements', endpoint.Achievements())
api.add_route('/achivements/{id}', endpoint.Achievement())
api.add_route('/categories', endpoint.Categories())
api.add_route('/categories/{id}', endpoint.Category())
api.add_route('/posts', endpoint.Posts())
api.add_route('/posts/{id}', endpoint.Post())
api.add_route('/tasks', endpoint.Tasks())
api.add_route('/tasks/{id}', endpoint.Task())
api.add_route('/threads', endpoint.Threads())
api.add_route('/threads/{id}', endpoint.Thread())
api.add_route('/users', endpoint.Users())
api.add_route('/users/{id}', endpoint.User())
api.add_route('/profile', endpoint.Profile())
api.add_route('/organisators', endpoint.Organisators())
api.add_route('/organisators/{id}', endpoint.Organisator())
api.add_route('/debug', endpoint.Debug())
