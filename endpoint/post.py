import json

from db import session
import model

from thread import Thread

def _post_to_json(post, reactions):
	return { 'id': post.id, 'parent_thread': post.thread, 'author': post.author, 'body': post.body,
		'published_at': post.published_at.isoformat(), 'reaction': reactions, 'is_new': False }

class Post(object):

	def on_options(self, req, resp, id):
		resp.set_header('Access-Control-Allow-Credentials', 'true')
		resp.set_header('Access-Control-Allow-Headers', 'content-type')
		resp.set_header('Access-Control-Allow-Methods', 'GET,HEAD,PUT,PATCH,POST,DELETE')

	def on_get(self, req, resp, id):
		post = session.query(model.Post).get(id)
		reactions = [ inst.id for inst in session.query(model.Post).filter(model.Post.parent == id) ]

		req.context['result'] = { 'post': _post_to_json(post, reactions) }


class Posts(object):
	def schema_generator(self, model_instances):
		return {'posts': [
			{'id': inst.id, 'title': inst.title, 'body': inst.body,
			 'time_published': inst.time_created} for inst in model_instances
		]}

	def on_options(self, req, resp):
		resp.set_header('Access-Control-Allow-Credentials', 'true')
		resp.set_header('Access-Control-Allow-Headers', 'content-type')
		resp.set_header('Access-Control-Allow-Methods', 'GET,HEAD,PUT,PATCH,POST,DELETE')

	def on_post(self, req, resp):
		data = json.loads(req.stream.read())
		post = model.Post(thread=data['post']['parent_thread'], body=data['post']['body'])

		session.add(post)
		session.commit()
		req.context['result'] = { 'post': _post_to_json(post, []) }
		session.close()

	def on_get(self, req, resp):
		posts = session.query(model.Post).all()
		req.context['result'] = self.schema_generator(posts)
