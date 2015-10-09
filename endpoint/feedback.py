import json

import util

class Feedback(object):

	def on_post(self, req, resp):
		data = json.loads(req.stream.read())

		if len(data['body']) == 0:
			return

		addr_from = data['email'] if len(data['email']) > 0 else util.mail.KSI
		util.mail.send(util.mail.KSI, '[KSI-WEB] Zpetna vazba', data['body'], addr_from)
