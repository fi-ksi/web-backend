import falcon
import json
from sqlalchemy import and_, text, not_, desc, func
from sqlalchemy.orm import load_only

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
		thread = session.query(model.Thread).get(id)

		if not thread or not thread.public:
			resp.status = falcon.HTTP_400
			return

		req.context['result'] = { 'thread': util.thread.to_json(thread, user_id) }
		session.close()


class Threads(object):

	def on_post(self, req, resp):
		user = req.context['user']
		if not user.is_logged_in():
			resp.status = falcon.HTTP_400
			return

		data = json.loads(req.stream.read())
		pblic = data['thread']['public'] if data['thread'].has_key('public') else True

		thread = model.Thread(title=data['thread']['title'], public=pblic, year = req.context['year'])
		session.add(thread)
		session.commit()
		req.context['result'] = { 'thread': util.thread.to_json(thread, user.id) }
		session.close()

	def on_get(self, req, resp):
		user_id = req.context['user'].id if req.context['user'].is_logged_in() else None
		show_all = (not (user_id is None)) and (req.context['user'].role == 'admin' or req.context['user'].role == 'org')

		# Hacky, nasty, whatever...
		task_threads = session.query(model.Task).options(load_only("thread")).all()
		task_threads = map(lambda x: x.thread, task_threads)

		threads = session.query(model.Thread).filter(model.Thread.public == True).\
			filter(model.Thread.year == req.context['year'])
		if not show_all:
			threads = threads.filter(not_(model.Thread.id.in_(task_threads)))
		threads = threads.order_by(desc(model.Thread.id)).all()

		req.context['result'] = { 'threads': [ util.thread.to_json(thread, user_id) for thread in threads] }
		session.close()


class ThreadDetails(object):

	def on_get(self, req, resp, id):
		user = req.context['user']
		thread = session.query(model.Thread).get(id)

		if not thread or not thread.public:
			resp.status = falcon.HTTP_400
			return

		last_visit = util.thread.get_visit(thread.id, user.id)

		req.context['result'] = {
			'threadDetails': util.thread.details_to_json(thread),
			'posts': [ util.post.to_json(post, user.id, last_visit) for post in thread.posts ]
		}
		session.close()
