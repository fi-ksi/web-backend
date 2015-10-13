import os
import datetime

from db import session
from model.module import ModuleType
import model
import util
import json

def modules_for_task(task_id):
	return session.query(model.Module).filter(model.Module.task == task_id).all()

def to_json(module, module_scores):
	has_points = False
	points = None

	for module_score in module_scores:
		if module_score.Module.id != module.id:
			continue

		has_points = True
		points = module_score.points
		break

	module_json = _info_to_json(module, module.id if has_points and points is not None else None)

	if has_points:
		module_json['state'] = 'correct' if points == module.max_points else 'incorrect'
	else:
		module_json['state'] = 'blank'

	if module.type == ModuleType.PROGRAMMING:
		code = util.programming.build(module.id)
		module_json['code'] = code
		module_json['default_code'] = code
		if not module.autocorrect:
			module_json['state'] = 'correct' if has_points else 'blank'
	elif module.type == ModuleType.QUIZ:
		module_json['questions'] = util.quiz.build(module.id)
	elif module.type == ModuleType.SORTABLE:
		module_json['sortable_list'] = util.sortable.build(module.id)
	elif module.type == ModuleType.GENERAL:
		module_json['state'] = 'correct' if has_points else 'blank'

	return module_json

def score_to_json(module_score):
	return {
		'id': module_score.Module.id,
		'is_corrected': module_score.points is not None,
		'score': module_score.points
	}

def submission_dir(module_id, user_id):
	return os.path.join('data', 'submissions', 'module_%d' % module_id, 'user_%d' % user_id)


def _info_to_json(module, score):
	return { 'id': module.id, 'type': module.type, 'name': module.name, 'description': module.description, 'autocorrect': module.autocorrect, 'max_score': module.max_points, 'score': score }

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
