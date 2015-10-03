import falcon
import json
from sqlalchemy import and_, text

from db import session
import model
import util

class Thread(object):

	def on_put(self, req, resp, id):
		user_id = req.context['user'].id if req.context['user'].is_logged_in() else None

		if not user_id:
			return

		if session.query(model.Thread).get(id) is None:
			status = falcon.HTTP_400
			return

		visit = util.thread.get_visit(user_id, id)

		if visit:
			visit.last_last_visit = visit.last_visit
		else:
			visit = model.ThreadVisit(thread=id, user=user_id)

		visit.last_visit = text('CURRENT_TIMESTAMP')

		session.add(visit)
		session.commit()
		session.close()

	def on_get(self, req, resp, id):
		user_id = req.context['user'].id if req.context['user'].is_logged_in() else None

		req.context['result'] = { 'thread': util.thread.to_json(session.query(model.Thread).get(id), user_id) }
		session.close()


class Threads(object):

	def on_post(self, req, resp):
		user = req.context['user']
		if not user.is_logged_in():
			resp.status = falcon.HTTP_400
			return

		data = json.loads(req.stream.read())
		thread = model.Thread(title=data['thread']['title'])

		session.add(thread)
		session.commit()
		req.context['result'] = { 'thread': util.thread.to_json(thread, user.id) }
		session.close()

	def on_get(self, req, resp):
		user_id = req.context['user'].id if req.context['user'].is_logged_in() else None

		req.context['result'] = { 'threads': [ util.thread.to_json(thread, user_id) for thread in session.query(model.Thread).all() ] }
		session.close()
