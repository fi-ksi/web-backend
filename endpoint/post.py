import json, falcon

from db import session
import model
import util

from thread import Thread

def _post_to_json(post, reactions):
	return { 'id': post.id, 'thread': post.thread, 'author': post.author, 'body': post.body,
		'published_at': post.published_at.isoformat(), 'reaction': reactions, 'is_new': False }

class Post(object):

	def on_put(self, req, resp, id):
		self.on_get(req, resp, id)

	def on_get(self, req, resp, id):
		post = session.query(model.Post).get(id)
		reactions = [ inst.id for inst in session.query(model.Post).filter(model.Post.parent == id) ]

		req.context['result'] = { 'post': _post_to_json(post, reactions) }


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

		req.context['result'] = { 'post': _post_to_json(post, []) }

		session.close()
