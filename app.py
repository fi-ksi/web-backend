import falcon
import json

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


#~ class Authorizer(object):
#~
	#~ def process_request(self, req, resp):
		#~ if req.auth:
			#~ token = session.query(model.Token).get(req.auth.split(' ')[-1])
#~
			#~ try:
				#~ req.context['id_user'] = token.owner.id
#~
				#~ if token.owner.admin:
					#~ req.context['permissions'] = 2
				#~ else:
					#~ req.context['permissions'] = 1
			#~ except AttributeError:
				#~ pass
#~
		#~ req.context['permissions'] = 0


def cors_middleware(request, response, params):
	origin = request.get_header('Origin')

	if origin in ('http://localhost:4200',):
		response.set_header('Access-Control-Allow-Origin', origin)

	response.set_header('Access-Control-Allow-Headers', 'Content-Type')
	response.set_header('Access-Control-Allow-Methods', 'OPTIONS')


api = falcon.API(before=[cors_middleware],
				 middleware=[JSONTranslator()]) #, Authorizer()])

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
api.add_route('/v1/oauth2/authorize', endpoint.Authorize())
api.add_route('/v1/oauth2/refresh', endpoint.Refresh())
