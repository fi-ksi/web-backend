import datetime
from sqlalchemy import func, distinct, or_

from db import session
import model

class TaskStatus:
	pass

def fully_submitted(user_id):
	max_modules_count = { task.id: task.modules for task in session.query(model.Task.id, func.count(model.Module.id).label('modules')).outerjoin(model.Module).group_by(model.Task.id).all() }

	real_modules_count = { task.id: task.modules for task in session.query(model.Task.id, func.count(distinct(model.Module.id)).label('modules')).join(model.Module).join(model.Evaluation).filter(model.Evaluation.user == user_id, or_(model.Module.autocorrect != True, model.Module.max_points == model.Evaluation.points)).group_by(model.Task.id).all() }

	return { int(key): int(val) for key, val in real_modules_count.items() if max_modules_count[key] == val }

def after_deadline():
	return { int(task.id) for task in session.query(model.Task).filter(model.Task.time_deadline < datetime.datetime.now() ).all() }

def currently_active(user_id=None):
	adeadline = after_deadline()

	if user_id is None:
		return adeadline

	return adeadline | set(fully_submitted(user_id).keys())

def max_points(task_id):
	points = session.query(func.sum(model.Module.max_points).label('points')).\
		filter(model.Module.task == task_id).first().points

	return int(points) if points else 0

def max_points_dict():
	points_per_task = session.query(model.Module.task.label('id'), func.sum(model.Module.max_points).label('points')).\
		group_by(model.Module.task).all()

	return { task.id: int(task.points) for task in points_per_task }

def points_per_module(task_id, user_id):
	return { module.module: module.points for module in session.query(model.Evaluation.module, func.max(model.Evaluation.points).label('points')).\
		join(model.Module, model.Evaluation.module == model.Module.id).\
		filter(model.Module.task == task_id, model.Evaluation.user == user_id).\
		group_by(model.Evaluation.module).all() }

def points(task_id, user_id):
	return sum(points_per_module(task_id, user_id).values())
