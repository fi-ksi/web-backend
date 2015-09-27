import json

class Module(object):

	def on_get(self, req, resp, id):

		req.context['result'] = { 'module': json.loads(open('modules.json').read())['modules'][0] }


class Modules(object):

	def on_get(self, req, resp):

		req.context['result'] = json.loads(open('modules.json').read())
