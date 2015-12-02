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

def _corr_eval_to_json(module, evaluation):
	res = {
		'id': evaluation.id,
		'points': evaluation.points,
		'last_modified': evaluation.time.isoformat(),
		'corrected_by': evaluation.evaluator,
		'full_report': evaluation.full_report
	}

	if module.type == model.module.ModuleType.GENERAL:
		res['general'] = _corr_general_to_json(module, evaluation)

	return res

# U modulu se zobrazuje jen jedno evaluation:
#  Pokud to ma byt nejadekvatnejsi evaluation, je \evl=None.
#  Pokud to ma byt specificke evaluation, je toto evalustion ulozeno v \evl
def _corr_module_to_json(evals, module, evl=None):
	if evl is None:
		# Ano, v Pythonu neexistuje max() pres dva klice
		evl = sorted(evals, key=lambda x: (x.points, x.time), reverse=True)[0]

	return {
		'module_id': module.id,
		'evaluations_list': [ evaluation.id for evaluation in evals ],
		'evaluation': _corr_eval_to_json(module, evl)
	}

# \modules je [(Evaluation, Module, specific_eval)] a je seskupeno podle modulu
#  specific_eval je Evaluation pokud se ma klientovi poslat jen jedno evaluation
# \evals je [Evaluation]
# \achievements je [Ahievement.id]
# \corrected je Bool
def to_json(modules, evals, task_id, thread_id=None, achievements=None, corrected=None):
	user_id = evals[0].user

	if thread_id is None: thread_id = util.task.comment_thread(task_id, user_id)
	if achievements is None: achievements = util.achievement.ids_list(util.achievement.per_task(user_id, task_id))
	if corrected is None: corrected = task_id in tasks_corrected()

	return {
		'id': task_id*100000 + user_id,
		'task_id': task_id,
		'state': 'corrected' if corrected else 'notcorrected',
		'user': user_id,
		'comment': thread_id,
		'achievements': achievements,
		'modules': [ _corr_module_to_json(filter(lambda x: x.module == module.id, evals), module, spec_evl) for (evl, module, spec_evl) in modules ]
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
