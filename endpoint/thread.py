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

		try:
			visit = util.thread.get_visit(user_id, id)

			if visit:
				visit.last_last_visit = visit.last_visit
				visit.last_visit = text('CURRENT_TIMESTAMP')
			else:
				visit = model.ThreadVisit(thread=id, user=user_id, last_visit=text('CURRENT_TIMESTAMP'))
				session.add(visit)

			session.commit()
			req.context['result'] = "{}"
		except:
			session.rollback()
			raise
		finally:
			session.close()

	def on_get(self, req, resp, id):
		user = req.context['user']
		user_id = req.context['user'].id if req.context['user'].is_logged_in() else None
		thread = session.query(model.Thread).get(id)

		if (not thread) or (not thread.public and not (user.is_org() or util.thread.is_eval_thread(user.id, thread.id))):
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

		try:
			thread = model.Thread(title=data['thread']['title'], public=pblic, year = req.context['year'])
			session.add(thread)
			session.commit()
		except:
			session.rollback()
			raise

		req.context['result'] = { 'thread': util.thread.to_json(thread, user.id) }
		session.close()

	"""
		Parametry: ?wave=integer filtruje vlakna k urcite vlne
	"""
	def on_get(self, req, resp):
		user_id = req.context['user'].id if req.context['user'].is_logged_in() else None
		show_all = (not (user_id is None)) and (req.context['user'].role == 'admin' or req.context['user'].role == 'org')

		wave = req.get_param_as_int('wave')

		threads = session.query(model.Thread, model.Task).\
			outerjoin(model.Task, model.Task.thread == model.Thread.id).\
			filter(model.Thread.public, model.Thread.year == req.context['year'])
		if wave: threads = threads.filter(model.Task.wave == wave)
		threads = threads.order_by(desc(model.Thread.id)).all()

		if not wave: threads = filter(lambda (thr,tsk): tsk == None, threads)

		req.context['result'] = { 'threads': [ util.thread.to_json(thread, user_id) for thread, task in threads] }
		session.close()


class ThreadDetails(object):

	def on_get(self, req, resp, id):
		user = req.context['user']
		thread = session.query(model.Thread).get(id)

		if (not thread) or (not thread.public and not (user.is_org() or util.thread.is_eval_thread(user.id, thread.id))):
			resp.status = falcon.HTTP_400
			return

		last_visit = util.thread.get_visit(thread.id, user.id)

		req.context['result'] = {
			'threadDetails': util.thread.details_to_json(thread),
			'posts': [ util.post.to_json(post, user.id, last_visit) for post in thread.posts ]
		}
		session.close()
