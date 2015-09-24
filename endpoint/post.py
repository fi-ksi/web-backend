from db import session
import model

from thread import Thread

class Post(object):

	def _post_to_json(self, post, reactions):
		return { 'id': post.id, 'author': post.author, 'body': post.body,
				 'published_at': post.published_at.isoformat(), 'reaction': reactions, 'is_new': False }

	def on_get(self, req, resp, id):
		post = session.query(model.Post).get(id)
		reactions = [ inst.id for inst in session.query(model.Post).filter(model.Post.parent == id) ]

		req.context['result'] = { 'post': self._post_to_json(post, reactions) }


class Posts(object):
	def schema_generator(self, model_instances):
		return {'posts': [
			{'id': inst.id, 'title': inst.title, 'body': inst.body,
			 'time_published': inst.time_created} for inst in model_instances
		]}

	def on_get(self, req, resp):
		posts = session.query(model.Post).all()
		req.context['result'] = self.schema_generator(posts)
