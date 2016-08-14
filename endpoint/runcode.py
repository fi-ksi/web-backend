# -*- coding: utf-8 -*-

import falcon
import json
from datetime import datetime

from db import session
from sqlalchemy.exc import SQLAlchemyError
import model
import util

class RunCode(object):

	def on_post(self, req, resp, id):
		try:
			user = req.context['user']
			if not user.is_logged_in():
				resp.status = falcon.HTTP_400
				return

			data = json.loads(req.stream.read())['content']
			module = session.query(model.Module).get(id)

			if not module:
				resp.status = falcon.HTTP_400
				return

			task_status = util.task.status(session.query(model.Task).get(module.task), user)

			if task_status == util.TaskStatus.LOCKED:
				resp.status = falcon.HTTP_400
				return

			req.context['result'] = util.programming.run(module, user.id, data)
		except SQLAlchemyError:
			session.rollback()
			raise
		finally:
			session.close()

