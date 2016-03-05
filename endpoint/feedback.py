# -*- coding: utf-8 -*-

import json

import util

class Feedback(object):

	def on_post(self, req, resp):
		data = json.loads(req.stream.read())

		if len(data['body']) == 0:
			return

		if not 'email' in data:
			data['email'] = "ksi@fi.muni.cz"

		util.mail.send_feedback(data['body'].encode('utf-8'), data['email'])

		req.context['result'] = { 'result': 'ok' }
