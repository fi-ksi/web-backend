import json, falcon

class Profile(object):
	def _schema(self, req):
		return {'profile': [
			{'id': 1, 'is_logged': bool(req.env['PERMISSIONS'])}
		]}

	def on_options(self, req, resp):
		resp.set_header('Access-Control-Allow-Credentials', 'true')
		resp.set_header('Access-Control-Allow-Headers', 'authorization')
		resp.set_header('Access-Control-Allow-Methods', 'GET,HEAD,PUT,PATCH,POST,DELETE')

		#resp.status = falcon.HTTP_204

	def on_get(self, req, resp):
		#req.context['result'] = self._schema(req)
		resp.set_header('X-Powered-By', 'Small Furry Creatures')
		req.context['result'] =  json.loads(' '.join(open('/tmp/profil.json').readlines()))
