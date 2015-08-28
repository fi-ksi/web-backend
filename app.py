import falcon
import json

import model
import resource
from db import engine


class JSONTranslator(object):

    def process_request(self, req, resp):
        return

    def process_response(self, req, resp, resource):
        if 'result' not in req.context:
            return

        resp.body = json.dumps(req.context['result'], sort_keys=True, indent=4)


def cors_middleware(request, response, params):
    origin = request.get_header('Origin')
    if origin in ('http://localhost:4200',):
        response.set_header(
            'Access-Control-Allow-Origin',
            origin
        )
    response.set_header(
        'Access-Control-Allow-Headers',
        'Content-Type'
    )
    # This could be overridden in the resource level
    response.set_header(
        'Access-Control-Allow-Methods',
        'OPTIONS'
    )


api = falcon.API(before=[cors_middleware], middleware=[JSONTranslator()])

model.Base.metadata.create_all(engine)

api.add_route('/articles', resource.Articles())
api.add_route('/articles/{id}', resource.Article())
api.add_route('/achivements', resource.Achievements())
api.add_route('/achivements/{id}', resource.Achievement())
api.add_route('/categories', resource.Categories())
api.add_route('/categories/{id}', resource.Category())
api.add_route('/posts', resource.Posts())
api.add_route('/posts/{id}', resource.Post())
api.add_route('/tasks', resource.Tasks())
api.add_route('/tasks/{id}', resource.Task())
api.add_route('/threads', resource.Threads())
api.add_route('/users', resource.Users())
api.add_route('/users/{id}', resource.User())
api.add_route('/profile', resource.Profile())
api.add_route('/organisators', resource.Organisators())
api.add_route('/organisators/{id}', resource.Organisator())
