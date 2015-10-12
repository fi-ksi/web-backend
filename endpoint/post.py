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

	def on_post(self, req, resp):
		if not req.context['user'].is_logged_in():
			resp.status = falcon.HTTP_400
			return

		user = req.context['user']
		user_id = user.id
		data = json.loads(req.stream.read())['post']

		thread_id = data['thread']
		thread = session.query(model.Thread).get(thread_id)

		if thread is None:
			resp.status = falcon.HTTP_400
			return

		if not thread.public:
			task_thread = session.query(model.Task).filter(model.Task.thread == thread_id).first()
			if task_thread and util.task.status(task_thread, user) == util.TaskStatus.LOCKED:
				resp.status = falcon.HTTP_400
				return

			solution_thread = session.query(model.SolutionComment).filter(model.SolutionComment.thread == thread_id, model.SolutionComment.user == user_id).first()
			if not solution_thread:
				resp.status = falcon.HTTP_400
				return

		parent = data['parent']
		if parent and not session.query(model.Post).filter(model.Post.id == parent, model.Post.thread == thread_id).first():
			resp.status = falcon.HTTP_400
			return

		post = model.Post(thread=thread_id, author=user_id, body=data['body'], parent=parent)

		session.add(post)
		session.commit()

		req.context['result'] = { 'post': util.post.to_json(post, user_id) }

		session.close()
