import json
from sqlalchemy import and_

from db import session
import model
import util

def _thread_to_json(thread, user_id):
	count = session.query(model.Post).filter(model.Post.thread == thread.id).count()

	if user_id:
		last_visit = session.query(model.ThreadVisit).filter(model.ThreadVisit.user == user_id, model.ThreadVisit.thread == thread.id).first()
		unread = count if not last_visit else session.query(model.Post).filter(model.Post.thread == thread.id, model.Post.published_at > last_visit.time).count()
	else:
		unread = 0

	root_posts = [ post.id for post in session.query(model.Post).filter(and_(model.Post.thread == thread.id, model.Post.parent == None)) ]

	return {
		"id": thread.id,
		"title": thread.title,
		"unread": unread,
		"posts_count": count,
		"root_posts": root_posts
		}

class Thread(object):

	def on_get(self, req, resp, id):
		user_id = None if not req.context['user'].is_logged_in() else req.context['user'].get_id()

		req.context['result'] = { 'thread': _thread_to_json(session.query(model.Thread).get(id), user_id) }
		session.close()


class Threads(object):

	def on_options(self, req, resp):
		util.fake_auth(req, resp)

	def on_post(self, req, resp):
		data = json.loads(req.stream.read())
		thread = model.Thread(title=data['thread']['title'])

		session.add(thread)
		session.commit()
		req.context['result'] = { 'thread': _thread_to_json(thread) }
		session.close()

	def on_get(self, req, resp):
		user_id = None if not req.context['user'].is_logged_in() else req.context['user'].get_id()

		req.context['result'] = { 'threads': [ _thread_to_json(thread, user_id) for thread in session.query(model.Thread).all() ] }
		session.close()
