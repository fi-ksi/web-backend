# -*- coding: utf-8 -*-`

import logging
import falcon
from sqlalchemy import func

from db import session
import model
import util

class Task(object):

	def on_get(self, req, resp, id):
		user = req.context['user']
		task = session.query(model.Task).get(id)

		if task is None:
			req.context['result'] = { 'errors': [ { 'status': '404', 'title': 'Not found', 'detail': u'Úloha s tímto ID neexistuje.' } ] }
			resp.status = falcon.HTTP_404
			return

		if (not user.is_logged_in()) or ((not user.is_org()) and (not user.is_tester())):
			if not task in session.query(model.Task).\
					join(model.Wave, model.Task.wave == model.Wave.id).\
					filter(model.Wave.public).all():
				resp.status = falcon.HTTP_400
				return

		req.context['result'] = { 'task': util.task.to_json(task, user) }


class Tasks(object):

	def on_get(self, req, resp):
		user = req.context['user']

		tasks = session.query(model.Task, model.Wave).\
		join(model.Wave, model.Task.wave == model.Wave.id)
		if (not user.is_logged_in()) or ((not user.is_org()) and not user.is_tester()):
			tasks = tasks.filter(model.Wave.public)
		tasks = tasks.filter(model.Wave.year == req.context['year']).all()

		adeadline = util.task.after_deadline()
		fsubmitted = util.task.fully_submitted(user.id, req.context['year'])
		corrected = util.task.corrected(user.id)
		autocorrected_full = util.task.autocorrected_full(user.id)
		task_max_points_dict = util.task.max_points_dict()

		req.context['result'] = { 'tasks': [ util.task.to_json(task.Task, user, adeadline, fsubmitted, task.Wave, task.Task.id in corrected, task.Task.id in autocorrected_full, task_max_points=task_max_points_dict[task.Task.id]) for task in tasks ] }


class TaskDetails(object):

	def on_get(self, req, resp, id):
		user = req.context['user']
		task = session.query(model.Task).get(id)
		if task is None:
			req.context['result'] = { 'errors': [ { 'status': '404', 'title': 'Not found', 'detail': u'Úloha s tímto ID neexistuje.' } ] }
			resp.status = falcon.HTTP_404
			return
		status = util.task.status(task, user)

		if status == util.TaskStatus.LOCKED:
			req.context['result'] = { 'errors': [ { 'status': '403', 'title': 'Forbudden', 'detail': u'Úloha uzamčena.' } ] }
			resp.status = falcon.HTTP_403
			return

		achievements = util.achievement.per_task(user.id, id)
		scores = util.task.points_per_module(id, user.id)
		best_scores = util.task.best_scores(id)

		comment_thread = util.task.comment_thread(id, user.id)
		thread_ids = { task.thread, comment_thread }
		threads = [ session.query(model.Thread).get(thread_id) for thread_id in thread_ids if thread_id is not None ]
		posts = []
		for thread in threads:
			posts += thread.posts

		req.context['result'] = {
			'taskDetails': util.task.details_to_json(task, user, status, achievements, best_scores, comment_thread),
			'modules': [ util.module.to_json(module, user.id) for module in task.modules ],
			'moduleScores': [ util.module.score_to_json(score) for score in scores if score.points is not None ],
			'achievements': [ util.achievement.to_json(achievement) for achievement in achievements ],
			'userScores': [ util.task.best_score_to_json(best_score) for best_score in best_scores ],
			'threads': [ util.thread.to_json(thread, user.id) for thread in threads ],
			'threadDetails': [ util.thread.details_to_json(thread) for thread in threads ],
			'posts': [util.post.to_json(post, user.id) for post in posts ]
		}

