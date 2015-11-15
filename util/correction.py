import datetime
from sqlalchemy import func, distinct, or_, and_, not_, desc
from sqlalchemy.dialects import mysql

from db import session
import model
import util
import os

def _corrected(evals):
	return evals.filter(and_(model.Evaluation.evaluator == None, not_(model.Module.autocorrect))).count() == 0

def _corr_general_to_json(module, evaluation):
	submittedFiles = session.query(model.SubmittedFile).\
		join(model.Evaluation, model.SubmittedFile.evaluation == evaluation.id).all()

	return {
		'files': [ {'id': inst.id, 'filename': os.path.basename(inst.path)} for inst in submittedFiles ]
	}

def _corr_module_to_json(evaluation):
	res = {
		'id': evaluation.module,
		'eval_id': evaluation.id,
		'points': evaluation.points,
		'last_modified': evaluation.time.isoformat(),
		'corrected_by': evaluation.evaluator
	}

	module = session.query(model.Module).get(evaluation.module)
	if module.type == model.module.ModuleType.GENERAL:
		res['general'] = _corr_general_to_json(module, evaluation)

	return res

# \evals je seskupeno podle module_id
def to_json(corr, evals):
	user = corr.Evaluation.user

	return {
		'id': corr.Task.id*100000 + user,
		'task_id': corr.Task.id,
		'state': 'corrected' if _corrected(evals) else 'notcorrected',
		'user': corr.Evaluation.user,
		'comment': util.task.comment_thread(corr.Task.id, user),
		'achievements': util.achievement.ids_list(util.achievement.per_task(user, corr.Task.id)),
		'modules': [ _corr_module_to_json(evl.Evaluation) for evl in evals ]
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
