import falcon

from db import session
import model
import util

class Task(object):

	def on_get(self, req, resp, id):
		task = session.query(model.Task).get(id)

		req.context['result'] = { 'task': util.task.to_json(task) }


class Tasks(object):

	def on_get(self, req, resp):
		user = req.context['user']
		tasks = session.query(model.Task).all()

		currently_active = util.task.currently_active(user.id)

		req.context['result'] = { 'tasks': [ util.task.to_json(task, currently_active=currently_active) for task in tasks ] }


class TaskDetails(object):

	def on_get(self, req, resp, id):
		user = req.context['user']
		task = session.query(model.Task).get(id)

		if task.prerequisite is not None and int(id) not in util.task.currently_active(user.id):
			resp.status = falcon.HTTP_400
			return

		scores = util.task.points_per_module(id, user.id)

		req.context['result'] = {
			'taskDetails': util.task.details_to_json(task),
			'modules': [ util.module.to_json(module, scores) for module in task.modules ],
			'moduleScores': [ util.module.score_to_json(score) for score in scores]
		}
