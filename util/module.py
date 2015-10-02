import datetime

from db import session
from model.module import ModuleType
import model
import util

def modules_for_task(task_id):
	return session.query(model.Module).filter(model.Module.task == task_id).all()

def to_json(module, module_scores):
	module_json = _info_to_json(module)

	score = module.id if [ score for score in module_scores if score.Module.id == module.id ] else None

	if module.type == ModuleType.PROGRAMMING:
		code = util.programming.build(module.id)
		module_json['code'] = code
		module_json['default_code'] = code
	elif module.type == ModuleType.QUIZ:
		module_json['questions'] = util.quiz.build(module.id)
	elif module.type == ModuleType.SORTABLE:
		module_json['sortable_list'] = util.sortable.build(module.id)

	return module_json

def score_to_json(module_score):
	return {
		'id': module_score.Module.id,
		'is_corrected': module_score.points is not None,
		'score': module_score.points
	}


def _info_to_json(module):
	return { 'id': module.id, 'type': module.type, 'name': module.name, 'description': module.description, 'autocorrect': module.autocorrect }

def _load_questions(module_id):
	return session.query(model.QuizQuestion).filter(model.QuizQuestion.module == module_id).order_by(model.QuizQuestion.order).all()

def _load_sortable(module_id):
	fixed = session.query(model.Sortable).filter(model.Sortable.module == module_id, model.Sortable.type == 'fixed').order_by(model.Sortable.order).all()
	movable = session.query(model.Sortable).filter(model.Sortable.module == module_id, model.Sortable.type == 'movable').order_by(model.Sortable.order).all()

	return (fixed, movable)
