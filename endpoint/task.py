import falcon
from sqlalchemy import func

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

		achievements = session.query(model.Achievement).join(model.UserAchievement).filter(model.UserAchievement.task_id == id, model.UserAchievement.user_id == user.id).all()
		scores = util.task.points_per_module(id, user.id)
		best_scores = util.task.best_scores(id)
		comment_thread = util.task.comment_thread(id, user.id)
		threads = [ task.thread, comment_thread ]

		req.context['result'] = {
			'taskDetails': util.task.details_to_json(task, achievements, best_scores, comment_thread),
			'modules': [ util.module.to_json(module, scores) for module in task.modules ],
			'moduleScores': [ util.module.score_to_json(score) for score in scores if score.points is not None ],
			'achievements': [ util.achievement.to_json(achievement) for achievement in achievements ],
			'threads': [ util.thread.to_json(session.query(model.Thread).get(thread_id), user.id) for thread_id in threads if thread_id is not None ],
			'userScores': [ util.task.best_score_to_json(best_score) for best_score in best_scores ]
		}
