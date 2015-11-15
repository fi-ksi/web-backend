import falcon
from sqlalchemy import func

from db import session
import model
import util

class CorrectionsPublish(object):

	"""
	Specifikace GET pozadavku:
	?public=(1|0)
		tento argument je nepovinny, pokud neni vyplnen, dojde ke zverejneni
	"""
	def on_get(self, req, resp, task_id):
		user = req.context['user']
		public = req.get_param('public')

		if (not user.is_logged_in()) or (not user.is_org()):
			resp.status = falcon.HTTP_400
			return

		if public is None: public = True

		task = session.query(model.Task).get(task_id)
		task.evaluation_public = public
		session.commit()
