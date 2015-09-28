import json
from sqlalchemy import func

from db import session
import model

from util import PrerequisitiesEvaluator, decode_form_data
import endpoint.module

# FAKE DATA!!!!
fake_valuation = { 1 : True, 2 : False }

def _load_submissions(task_id, user_id):
	return session.query(model.Submission).filter(model.Submission.task == task_id, model.Submission.user == user_id).all()

def max_points_dict():
	points_per_task = session.query(model.Module.task.label('id'), func.sum(model.Module.max_points).label('points')).\
		group_by(model.Module.task).all()

	print { task.id: int(task.points) for task in points_per_task }

	return { task.id: int(task.points) for task in points_per_task }

def _max_points_for_task(task_id):
	points = session.query(func.sum(model.Module.max_points).label('points')).\
		filter(model.Module.task == task_id).first().points

	return int(points) if points else 0

def _load_points_for_user(task_id, user_id):
	return session.query(model.Evaluation.module, func.max(model.Evaluation.points).label('points')).\
		join(model.Submission, model.Evaluation.submission == model.Submission.id).\
		filter(model.Submission.task == task_id, model.Submission.user == user_id).\
		group_by(model.Evaluation.module).all()

def _sum_points(task_id, user_id):
	return sum([ item.points for item in _load_points_for_user(task_id, user_id) ])

def _task_to_json(task, points=None):
	try:
		max_score = points[task.id] if points else _max_points_for_task(task.id)
	except KeyError:
		max_score = 0

	return {
		'id': task.id,
		'title': task.title,
		'author': task.author,
		'category': task.category,
		'intro': task.intro,
		'body': task.body,
		'max_score': max_score,
		'position': [ task.position_x, task.position_y ],
		'thread': task.thread,
		'time_published': task.time_published.isoformat(),
		'time_deadline': task.time_deadline.isoformat(),
		'node_parent': [ parent.parent_id for parent in task.parents ],
		'active': True if task.prerequisite_obj is None else PrerequisitiesEvaluator(fake_valuation, task.prerequisite_obj).evaluate(),
		'modules': [ module.id for module in task.modules ],
		'best_scores': [ 1 ],
		'my_score': _sum_points(task.id, 1),
		'solution': 'Prehledne vysvetlene reseni prikladu. Cely priklad spocival v blabla',
		'prerequisities': [],
		'submissions': [ submission.id for submission in _load_submissions(task.id, 1) ],
		'picture_active': 'img/nodes/vlna-1/node-big-travelling/base.svg',
		'picture_locked': 'img/nodes/vlna-1/node-big-travelling/base.svg',
		'picture_submitted': 'img/nodes/vlna-1/node-big-travelling/base.svg',
		'picture_finished': 'img/nodes/vlna-1/node-big-travelling/base.svg',
	}

class Task(object):

	def on_get(self, req, resp, id):
		task = session.query(model.Task).get(id)

		req.context['result'] = { 'task': _task_to_json(task) }


class Tasks(object):

	def on_get(self, req, resp):
		tasks = session.query(model.Task).all()
		points_dict = max_points_dict()

		req.context['result'] = { 'tasks': [ _task_to_json(task, points_dict) for task in tasks ] }

class TaskSubmit(object):

	def on_post(self, req, resp, id):
		data = decode_form_data(req)
		evaluations = {}

		for (key, val) in data.items():
			val = val[0]
			module_id = int(key.split('_')[1])
			solution = json.loads(val)['solution']

			module = session.query(model.Module).get(module_id)

			if module.type == 'quiz':
				result, report = endpoint.module.quiz_evaluate(id, module_id, solution)
			elif module.type == 'sortable':
				result, report = endpoint.module.sortable_evaluate(id, module_id, solution)

			evaluations[module.id] = (module.max_points if result else 0, report)

		submission = model.Submission(task=id, user=1)
		session.add(submission)
		session.commit()

		for module, data in evaluations.items():
			evaluation = model.Evaluation(submission=submission.id, module=module, points=data[0], full_report=data[1])
			session.add(evaluation)

		session.commit()
		session.close()
