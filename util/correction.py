import datetime
from sqlalchemy import func, distinct, or_, and_, not_, desc
from sqlalchemy.dialects import mysql

from db import session
import model
import util
import os

# Vraci seznam plne opravenych uloh (tj. takovych uloh, kde jsou vsechna reseni jiz opravena)
def tasks_corrected():
	task_corrected = session.query(model.Task.id.label('task_id'), (func.count(model.Evaluation) > 0).label('notcorrected')).\
		join(model.Module, model.Module.task == model.Task.id).\
		join(model.Evaluation, model.Module.id == model.Evaluation.module).\
		filter(model.Evaluation.evaluator == None, not_(model.Module.autocorrect)).\
		group_by(model.Task).subquery()

	return  [ r for (r, ) in session.query(model.Task.id).\
		outerjoin(task_corrected, task_corrected.c.task_id == model.Task.id).\
		filter(or_(task_corrected.c.notcorrected == False, task_corrected.c.notcorrected == None))
	]


def _corr_general_to_json(module, evaluation):
	submittedFiles = session.query(model.SubmittedFile).\
		join(model.Evaluation, model.SubmittedFile.evaluation == evaluation.id).all()

	return {
		'files': [ {'id': inst.id, 'filename': os.path.basename(inst.path)} for inst in submittedFiles ]
	}

def _corr_module_to_json(evaluation, module):
	res = {
		'id': module.id,
		'eval_id': evaluation.id,
		'points': evaluation.points,
		'last_modified': evaluation.time.isoformat(),
		'corrected_by': evaluation.evaluator
	}

	if module.type == model.module.ModuleType.GENERAL:
		res['general'] = _corr_general_to_json(module, evaluation)

	return res

# \evals je (Evaluation, Module) a je seskupeno podle modulu
def to_json(corr, evals, thread_id=None, achievements=None, corrected=None):
	user = corr.Evaluation.user

	if thread_id is None: thread_is = util.task.comment_thread(corr.Task.id, user)
	if achievements is None: achievements = util.achievement.ids_list(util.achievement.per_task(user, corr.Task.id))
	if corrected is None: corrected = corr.Task.id in tasks_corrected()

	return {
		'id': corr.Task.id*100000 + user,
		'task_id': corr.Task.id,
		'state': 'corrected' if corrected else 'notcorrected',
		'user': corr.Evaluation.user,
		'comment': thread_id,
		'achievements': achievements,
		'modules': [ _corr_module_to_json(evl, module) for (evl, module) in evals ]
	}

def module_to_json(module):
	return {
		'id': module.id,
		'type': module.type,
		'name': module.name,
		'autocorrect': module.autocorrect,
		'max_points': module.max_points
	}

def task_to_json(task):
	return {
		'id': task.id,
		'title': task.title
	}
