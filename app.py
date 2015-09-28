import falcon, json
from datetime import datetime

import model
import endpoint
from db import engine, session
from util import UserInfo


class JSONTranslator(object):

	def process_request(self, req, resp):
		return

	def process_response(self, req, resp, endpoint):
		if 'result' not in req.context:
			return

		resp.body = json.dumps(req.context['result'], sort_keys=True, indent=4)


class Authorizer(object):

	def process_request(self, req, resp):
		if req.auth:
			token = session.query(model.Token).get(req.auth.split(' ')[-1])

			try:
				req.context['user'] = UserInfo(session.query(model.User).get(token.id_user))
				return
			except AttributeError:
				pass

		req.context['user'] = UserInfo()

def log(req, resp):
	try:
		ip = req.env['HTTP_X_FORWARDED_FOR'].split(',')[-1].strip()
	except KeyError:
		ip = req.env['REMOTE_ADDR']

	print '[%s] [%s] [%s] [%s] %s' % (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), ip, req.method, resp.status, req.relative_uri)

def log_middleware(req, resp, params):
	log(req, resp)

def log_sink(req, resp):
	resp.status = falcon.HTTP_404

	log(req, resp)

def cors_middleware(request, response, params):
	origin = request.get_header('Origin')

	if origin in ('http://localhost:4200',):
		response.set_header('Access-Control-Allow-Origin', origin)

	response.set_header('Access-Control-Allow-Headers', 'authorization,content-type')
	response.set_header('Access-Control-Allow-Methods', 'OPTIONS,PUT,POST,GET')


api = falcon.API(before=[ cors_middleware ], after=[ log_middleware ],
				 middleware=[JSONTranslator(), Authorizer()])


model.Base.metadata.create_all(engine)

api.add_route('/articles', endpoint.Articles())
api.add_route('/articles/{id}', endpoint.Article())
api.add_route('/achievements', endpoint.Achievements())
api.add_route('/achievements/{id}', endpoint.Achievement())
api.add_route('/categories', endpoint.Categories())
api.add_route('/categories/{id}', endpoint.Category())
api.add_route('/posts', endpoint.Posts())
api.add_route('/posts/{id}', endpoint.Post())
api.add_route('/tasks', endpoint.Tasks())
api.add_route('/tasks/{id}', endpoint.Task())
api.add_route('/task/{id}/submit', endpoint.TaskSubmit())
api.add_route('/modules/{id}', endpoint.Module())
api.add_route('/threads', endpoint.Threads())
api.add_route('/threads/{id}', endpoint.Thread())
api.add_route('/users', endpoint.Users())
api.add_route('/users/{id}', endpoint.User())
api.add_route('/scores/{id}', endpoint.Score())
api.add_route('/profile', endpoint.Profile())
api.add_route('/registration', endpoint.Registration())
api.add_route('/organisators', endpoint.Organisators())
api.add_route('/organisators/{id}', endpoint.Organisator())
api.add_route('/debug', endpoint.Debug())
api.add_route('/v1/oauth2/authorize', endpoint.Authorize())
api.add_route('/v1/oauth2/refresh', endpoint.Refresh())
api.add_sink(log_sink)
