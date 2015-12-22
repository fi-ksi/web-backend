from db import session
import model
import util
import falcon
import json
import datetime

class Merge(object):

	def on_post(self, req, resp, id):
		user = req.context['user']

		if (not user.is_logged_in()) or (not user.is_org()):
			resp.status = falcon.HTTP_400
			return


