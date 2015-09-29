import json
from sqlalchemy import func

from db import session
import model

from util import PrerequisitiesEvaluator, decode_form_data
import endpoint.module

# FAKE DATA!!!!
fake_valuation = { 1: True, 2: False, 3: True, 4: True, 5: True, 6: True }

def max_points_dict():
	points_per_task = session.query(model.Module.task.label('id'), func.sum(model.Module.max_points).label('points')).\
		group_by(model.Module.task).all()

	return { task.id: int(task.points) for task in points_per_task }

def _max_points_for_task(task_id):
	points = session.query(func.sum(model.Module.max_points).label('points')).\
		filter(model.Module.task == task_id).first().points

	return int(points) if points else 0

def _load_points_for_user(task_id, user_id):
	return session.query(model.Evaluation.module, func.max(model.Evaluation.points).label('points')).\
		join(model.Module, model.Evaluation.module == model.Module.id).\
		filter(model.Module.task == task_id, model.Evaluation.user == user_id).\
		group_by(model.Evaluation.module).all()

def sum_points(task_id, user_id):
	return sum([ item.points for item in _load_points_for_user(task_id, user_id) ])

def _prerequisities_to_json(prereq):
		if(prereq.type == 'ATOMIC'):
			return [ [ prereq.task ] ]

		if(prereq.type == 'AND'):
			return [ [ child.task for child in prereq.children ] ]

		if(prereq.type == 'OR'):
			return [ _prerequisities_to_json2(child) for child in prereq.children ]

def _prerequisities_to_json2(prereq):
		if(prereq.type == 'ATOMIC'):
			return [ prereq.task ]

		if(prereq.type == 'AND'):
			return [ child.task for child in prereq.children ]

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
		'active': True if task.prerequisite_obj is None else PrerequisitiesEvaluator(fake_valuation, task.prerequisite_obj).evaluate(),
		'modules': [ module.id for module in task.modules ],
		'best_scores': [ 1 ],
		'my_score': sum_points(task.id, 1),
		'solution': 'Prehledne vysvetlene reseni prikladu. Cely priklad spocival v blabla',
		'submissions': [],
		'prerequisities': [] if not task.prerequisite_obj else _prerequisities_to_json(task.prerequisite_obj),
		'picture_base': task.picture_base,
		'picture_suffix': '.svg'
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
