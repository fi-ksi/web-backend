import json

import util

class Feedback(object):

	def on_post(self, req, resp):
		data = json.loads(req.stream.read())

		if len(data['body']) == 0:
			return

		util.mail.send_feedback(data['body'], data['email'])

		req.context['result'] = { 'result': 'ok' }
