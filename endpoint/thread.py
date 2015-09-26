import json
from sqlalchemy import and_

from db import session
import model
import util

def _thread_to_json(thread):
	unread = 3
	count = session.query(model.Post).filter(model.Post.thread == thread.id).count()
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
		req.context['result'] = { 'thread': _thread_to_json(session.query(model.Thread).get(id)) }
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
		req.context['result'] = { 'threads': [ _thread_to_json(thread) for thread in session.query(model.Thread).all() ] }
		session.close()
