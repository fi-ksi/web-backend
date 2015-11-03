import os
import datetime

from sqlalchemy import func, desc
from db import session
from model.module import ModuleType
import model
import util
import json

def modules_for_task(task_id):
	return session.query(model.Module).filter(model.Module.task == task_id).all()

# Pokud existuje evaluation modulu \module_id uzivatele \user_id,
# vrati seznam vsech ID takovychto evaluation
# napr. [12, 34]
def existing_evaluation(module_id, user_id):
	results = session.query(model.Evaluation.id).\
		filter(model.Evaluation.user == user_id).\
		join(model.Module, model.Module.id == model.Evaluation.module).\
		filter(model.Module.id == module_id).all()
	return [ r for (r, ) in results ]

def to_json(module, user_id):
	module_json = _info_to_json(module)

	# Nejdriv zjistime, jestli mame nejake evaluations
	count = session.query(model.Evaluation.points).filter(model.Evaluation.user == user_id, model.Evaluation.module == module.id).\
			join(model.Module, model.Module.id == model.Evaluation.module).\
			join(model.Task, model.Task.id == model.Module.task).count()

	best_status = session.query(func.max(model.Evaluation.points).label('points')).\
		filter(model.Evaluation.user == user_id, model.Evaluation.module == module.id).\
		join(model.Module, model.Module.id == model.Evaluation.module).\
		join(model.Task, model.Task.id == model.Module.task).\
		filter(model.Task.evaluation_public).first()

	if count > 0:
		# ziskame nejlepsi evaluation a podle toho rozhodneme, jak je na tom resitel
		module_json['state'] = 'correct' if best_status.points == module.max_points else 'incorrect'
	else:
		module_json['state'] = 'blank'

	module_json['score'] = module.id if best_status.points else None

	if module.type == ModuleType.PROGRAMMING:
		code = util.programming.build(module.id)
		module_json['code'] = code
		module_json['default_code'] = code
		if not module.autocorrect:
			module_json['state'] = 'correct' if count > 0 else 'blank'
	elif module.type == ModuleType.QUIZ:
		module_json['questions'] = util.quiz.build(module.id)
	elif module.type == ModuleType.SORTABLE:
		module_json['sortable_list'] = util.sortable.build(module.id)
	elif module.type == ModuleType.GENERAL:
		module_json['state'] = 'correct' if count > 0 else 'blank'

		submittedFiles = session.query(model.SubmittedFile).\
			join(model.Evaluation, model.SubmittedFile.evaluation == model.Evaluation.id).\
			filter(model.Evaluation.user == user_id, model.Evaluation.module == module.id).all()

		submittedFiles = [ {'id': inst.id, 'filename': os.path.basename(inst.path)} for inst in submittedFiles ]

		module_json['submitted_files'] = submittedFiles
	elif module.type == ModuleType.TEXT:
		module_json['fields'] = util.text.num_fields(module.id)

	return module_json

def score_to_json(module_score):
	return {
		'id': module_score.Module.id,
		'is_corrected': module_score.points is not None,
		'score': module_score.points
	}

def submission_dir(module_id, user_id):
	return os.path.join('data', 'submissions', 'module_%d' % module_id, 'user_%d' % user_id)


def _info_to_json(module):
	return { 'id': module.id, 'type': module.type, 'name': module.name, 'description': module.description, 'autocorrect': module.autocorrect, 'max_score': module.max_points }

def _load_questions(module_id):
	return session.query(model.QuizQuestion).filter(model.QuizQuestion.module == module_id).order_by(model.QuizQuestion.order).all()

def _load_sortable(module_id):
	fixed = session.query(model.Sortable).filter(model.Sortable.module == module_id, model.Sortable.type == 'fixed').order_by(model.Sortable.order).all()
	movable = session.query(model.Sortable).filter(model.Sortable.module == module_id, model.Sortable.type == 'movable').order_by(model.Sortable.order).all()

	return (fixed, movable)

def perform_action(module, user):
	if not module.action:
		return
	action = json.loads(module.action)
	if u"action" in action:
		if action[u"action"] == u"add_achievement":
			achievement = model.UserAchievement(user_id=user.id, achievement_id=action[u"achievement_id"],task_id=module.task)
			already_done = session.query(model.UserAchievement).filter(model.UserAchievement.user_id==user.id, model.UserAchievement.achievement_id==action[u"achievement_id"], model.UserAchievement.task_id==module.task).first()
			if not already_done:
				session.add(achievement)
		else:
			print("Unknown action!")
			# ToDo: More actions
