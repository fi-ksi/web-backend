import json, falcon

from db import session
import model
import util

from thread import Thread

class Post(object):

	def on_put(self, req, resp, id):
		self.on_get(req, resp, id)

	def on_get(self, req, resp, id):
		user_id = req.context['user'].get_id() if req.context['user'].is_logged_in() else None

		post = session.query(model.Post).get(id)

		req.context['result'] = { 'post': util.post.to_json(post, user_id) }


class Posts(object):

	#TODO: Zabezpecit
	def on_post(self, req, resp):
		if not req.context['user'].is_logged_in():
			resp.status = falcon.HTTP_400
			return

		user_id = req.context['user'].get_id()
		data = json.loads(req.stream.read())['post']
		post = model.Post(thread=data['thread'], author=user_id, body=data['body'], parent=data['parent'])

		session.add(post)
		session.commit()

		req.context['result'] = { 'post': util.post.to_json(post, user_id) }

		session.close()
