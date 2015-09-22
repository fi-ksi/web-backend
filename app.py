import falcon
import json

from oauthlib.oauth2 import RequestValidator
from oauthlib.oauth2 import WebApplicationServer

import model
import endpoint
from db import engine


class JSONTranslator(object):

    def process_request(self, req, resp):
        return

    def process_response(self, req, resp, endpoint):
        if 'result' not in req.context:
            return

        resp.body = json.dumps(req.context['result'], sort_keys=True, indent=4)


class MyRequestValidator(RequestValidator):

    def validate_client_id(self, client_id, request):
        return True

    def get_default_redirect_uri(sellf, client_id, *args, **kwargs):
        return '127.0.0.1'


def cors_middleware(request, response, params):
    origin = request.get_header('Origin')

    if origin in ('http://localhost:4200',):
        response.set_header('Access-Control-Allow-Origin', origin)

    response.set_header('Access-Control-Allow-Headers', 'Content-Type')
    response.set_header('Access-Control-Allow-Methods', 'OPTIONS')


validator = MyRequestValidator()
authz = WebApplicationServer(validator)


api = falcon.API(before=[cors_middleware],
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
api.add_route('/v1/oauth2/auth', endpoint.Auth())
api.add_route('/v1/oauth2/token', endpoint.Token())
