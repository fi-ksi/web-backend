import datetime
from sqlalchemy import func, distinct, or_, and_, not_, desc
from sqlalchemy.dialects import mysql

from db import session
import model
import util

def user_to_json(user):
	return {
		'id': user.id,
		'first_name': user.first_name,
		'last_name': user.last_name,
		'role': user.role
	}

def _task_corr_state(task):
	if task.evaluation_public: return "published"
	evals = session.query(model.Evaluation, model.Module).\
		join(model.Module, model.Module.id == model.Evaluation.module).\
		join(model.Task, model.Task.id == model.Module.task).\
		filter(model.Task.id == task.id)
	if util.correction.evals_corrected(evals): return "corrected"
	if evals.filter(model.Evaluation.evaluator != None).count() > 0: return "working"
	return "base"

def task_to_json(task):
	q = session.query(model.User.id).\
		join(model.Evaluation, model.Evaluation.user == model.User.id).\
		join(model.Module, model.Module.id == model.Evaluation.module).\
		join(model.Task, model.Module.task == model.Task.id).\
		filter(model.Task.id == task.id).group_by(model.User).all()
	solvers = [ r for (r, ) in q ]

	return {
		'id': task.id,
		'title': task.title,
		'wave': task.wave,
		'author': task.author,
		'corr_state': _task_corr_state(task),
		'solvers': solvers
	}
