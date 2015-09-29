import json, falcon

from db import session
import model
import util

from thread import Thread

def _post_to_json(post, reactions, user_id):
	if user_id:
		last_visit = session.query(model.ThreadVisit).filter(model.ThreadVisit.user == user_id, model.ThreadVisit.thread == post.thread).first()
		is_new = True if not last_visit else last_visit.time < post.published_at
	else:
		is_new = False

	return { 'id': post.id, 'thread': post.thread, 'author': post.author, 'body': post.body,
		'published_at': post.published_at.isoformat(), 'reaction': reactions, 'is_new': is_new }

class Post(object):

	def on_put(self, req, resp, id):
		self.on_get(req, resp, id)

	def on_get(self, req, resp, id):
		user_id = req.context['user'].get_id() if req.context['user'].is_logged_in() else None

		post = session.query(model.Post).get(id)
		reactions = [ inst.id for inst in session.query(model.Post).filter(model.Post.parent == id) ]

		req.context['result'] = { 'post': _post_to_json(post, reactions, user_id) }


class Posts(object):

	def on_post(self, req, resp):
		if not req.context['user'].is_logged_in():
			resp.status = falcon.HTTP_400
			return

		user_id = req.context['user'].get_id()
		data = json.loads(req.stream.read())['post']
		post = model.Post(thread=data['thread'], author=user_id, body=data['body'], parent=data['parent'])

		session.add(post)
		session.commit()

		req.context['result'] = { 'post': _post_to_json(post, [], user_id) }

		session.close()
