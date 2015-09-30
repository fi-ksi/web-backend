import json
from sqlalchemy import and_, text

from db import session
import model

def _get_visit(user_id, thread_id):
	return session.query(model.ThreadVisit).filter(model.ThreadVisit.user == user_id, model.ThreadVisit.thread == thread_id).first()

def _unread_posts_count(user_id, thread_id):
	if not user_id:
		return 0

	visit = _get_visit(user_id, thread_id)

	if not visit:
		return None

	return session.query(model.Post).filter(model.Post.thread == thread_id, model.Post.published_at > visit.last_visit).count()

def _thread_to_json(thread, user_id):
	count = session.query(model.Post).filter(model.Post.thread == thread.id).count()
	unread = _unread_posts_count(user_id, thread.id)
	root_posts = [ post.id for post in session.query(model.Post).filter(and_(model.Post.thread == thread.id, model.Post.parent == None)) ]

	return {
		'id': thread.id,
		'title': thread.title,
		'unread': unread if unread is not None else count,
		'posts_count': count,
		'root_posts': root_posts
	}

class Thread(object):

	def on_put(self, req, resp, id):
		user_id = req.context['user'].id if req.context['user'].is_logged_in() else None

		if not user_id:
			return

		visit = _get_visit(user_id, id)

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

		req.context['result'] = { 'thread': _thread_to_json(session.query(model.Thread).get(id), user_id) }
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
		req.context['result'] = { 'thread': _thread_to_json(thread, user.id) }
		session.close()

	def on_get(self, req, resp):
		user_id = req.context['user'].id if req.context['user'].is_logged_in() else None

		req.context['result'] = { 'threads': [ _thread_to_json(thread, user_id) for thread in session.query(model.Thread).all() ] }
		session.close()
