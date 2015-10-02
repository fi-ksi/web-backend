import datetime
from sqlalchemy import func, distinct, or_

from db import session
import model
import util

class TaskStatus:
	pass

def fully_submitted(user_id):
	max_modules_count = { task.id: task.modules for task in session.query(model.Task.id, func.count(model.Module.id).label('modules')).outerjoin(model.Module).group_by(model.Task.id).all() }

	real_modules_count = { task.id: task.modules for task in session.query(model.Task.id, func.count(distinct(model.Module.id)).label('modules')).join(model.Module).join(model.Evaluation).filter(model.Evaluation.user == user_id, or_(model.Module.autocorrect != True, model.Module.max_points == model.Evaluation.points)).group_by(model.Task.id).all() }

	return { int(key): int(val) for key, val in real_modules_count.items() if max_modules_count[key] == val }

def after_deadline():
	return { int(task.id) for task in session.query(model.Task).filter(model.Task.time_deadline < datetime.datetime.now() ).all() }

def currently_active(user_id=None):
	if user_id is None:
		return []

	return after_deadline() | set(fully_submitted(user_id).keys())

def max_points(task_id):
	points = session.query(func.sum(model.Module.max_points).label('points')).\
		filter(model.Module.task == task_id).first().points

	return int(points) if points else 0

def max_points_dict():
	points_per_task = session.query(model.Module.task.label('id'), func.sum(model.Module.max_points).label('points')).\
		group_by(model.Module.task).all()

	return { task.id: int(task.points) for task in points_per_task }

def points_per_module(task_id, user_id):
	return session.query(model.Module, \
		func.max(model.Evaluation.points).label('points')).\
		join(model.Evaluation, model.Evaluation.module == model.Module.id).\
		filter(model.Module.task == task_id, model.Evaluation.user == user_id).\
		group_by(model.Evaluation.module).all()

def points(task_id, user_id):
	ppm = points_per_module(task_id, user_id)

	if len(ppm) == 0:
		return None

	return sum(module.points for module in ppm if module.points is not None)

def to_json(task, user_id=None, currently_active=None):
	max_points = sum([ module.max_points for module in task.modules ])

	if not currently_active:
		currently_active = util.task.currently_active(user_id)

	is_active = True if task.id in currently_active else util.PrerequisitiesEvaluator(task.prerequisite_obj, currently_active).evaluate()

	return {
		'id': task.id,
		'title': task.title,
		'author': task.author,
		'category': task.category,
		'intro': task.intro,
		'max_score': sum([ module.max_points for module in task.modules ]),
		'position': [ task.position_x, task.position_y ],
		'time_published': task.time_published.isoformat(),
		'time_deadline': task.time_deadline.isoformat(),
		'state': 'done' if is_active else 'locked',
		'prerequisities': [] if not task.prerequisite_obj else util.prerequisite.to_json(task.prerequisite_obj),
		'picture_base': task.picture_base,
		'picture_suffix': '.svg'
	}

def details_to_json(task, achievements):
	return {
		'id': task.id,
		'body': task.body,
		'thread': task.thread,
		'time_published': task.time_published.isoformat(),
		'time_deadline': task.time_deadline.isoformat(),
		'modules': [ module.id for module in task.modules ],
		'best_scores': [ 1 ],
		'solution': 'Prehledne vysvetlene reseni prikladu. Cely priklad spocival v blabla',
		'achievements': [ achievement.id for achievement in achievements ]
	}
