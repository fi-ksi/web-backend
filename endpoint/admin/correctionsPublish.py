# -*- coding: utf-8 -*-

import falcon
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from db import session
import model
import util

class CorrectionsPublish(object):

	"""
	Specifikace GET pozadavku:
	?public=(1|0)
		tento argument je nepovinny, pokud neni vyplnen, dojde ke zverejneni
	"""
	def on_get(self, req, resp, id):
		try:
			user = req.context['user']
			public = req.get_param_as_bool('public')

			if (not user.is_logged_in()) or (not user.is_org()):
				resp.status = falcon.HTTP_400
				return

			if public is None: public = True

			task = session.query(model.Task).get(id)
			if task is None:
				resp.status = falcon.HTTP_404
				return
			task.evaluation_public = public
			session.commit()
			req.context['result'] = "{}"
		except SQLAlchemyError:
			session.rollback()
			raise
		finally:
			session.close()

