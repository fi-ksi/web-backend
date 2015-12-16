from db import session
import model
import util

def fake_profile():
	return { 'profile': { 'id': 0, 'signed_in': False } }

def to_json(user, profile, year_id):
	task_scores = { task: points for task, points in util.task.any_submitted(user.id, year_id) }

	adeadline = util.task.after_deadline()
	fsubmitted = util.task.fully_submitted(user.id, year_id)
	corrected = util.task.corrected(user.id)
	autocorrected_full = util.task.autocorrected_full(user.id)

	# task_achievements je seznam [(Task,Achievement)] pro vsechny achievementy uzivatele user v uloze Task
	task_achievements = session.query(model.Task, model.Achievement).\
		join(model.UserAchievement, model.UserAchievement.task_id == model.Task.id).\
		join(model.Achievement, model.UserAchievement.achievement_id == model.Achievement.id).\
		filter(model.UserAchievement.user_id == user.id, model.Achievement.year == year_id).\
		group_by(model.Task, model.Achievement).all()

	return {
			'profile': [ _profile_to_json(user, profile, task_scores, year_id) ],
			'tasks': [ util.task.to_json(task, user, adeadline, fsubmitted, None, task.id in corrected, task.id in autocorrected_full) for task in task_scores.keys() ],
			'taskScores': [ task_score_to_json(task, points, user, \
					[ ach.id for (_, ach) in filter(lambda (tsk, ach): tsk.id == task.id, task_achievements) ]) \
				for task, points in task_scores.items() ]
	}

def _profile_to_json(user, profile, task_scores, year_id):
	points = util.user.sum_points(user.id, year_id)
	summary = sum(util.task.max_points_dict().values())
	successful = round((float(points)/summary) * 100) if summary != 0 else 0

	return {
			'id': user.id,
			'signed_in': True,
			'first_name': user.first_name,
			'last_name': user.last_name,
			'profile_picture': util.user.get_profile_picture(user),
			'short_info': user.short_info,
			'email': user.email,
			'gender': user.sex,
			'addr_street': profile.addr_street,
			'addr_city': profile.addr_city,
			'addr_zip': profile.addr_zip,
			'addr_country': profile.addr_country,
			'school_name': profile.school_name,
			'school_street': profile.school_street,
			'school_city': profile.school_city,
			'school_zip': profile.school_zip,
			'school_country': profile.school_country,
			'school_finish': profile.school_finish,
			'tshirt_size': profile.tshirt_size,
			'achievements': list(util.achievement.ids_set(util.user.achievements(user.id, year_id))),
			'percentile': util.user.percentile(user.id, year_id),
			'score': format(points, '.1f'),
			'seasons': util.user.active_years(user.id),
			'successful': int(successful),
			'results': [ task.id for task in task_scores.keys() ],
			'role': user.role,
			'tasks_num': len(util.task.fully_submitted(user.id, year_id))
	}

# \achievements ocekava seznam ID achievementu nebo None
def task_score_to_json(task, points, user, achievements=None):
	if achievements is None:
		achievements = [ achievement.achievement_id for achievement in session.query(model.UserAchievement).filter(model.UserAchievement.user_id == user.id, model.UserAchievement.task_id == task.id).all()]

	return {
			'id': task.id,
			'task': task.id,
			'achievements': achievements,
			'score': format(points, '.1f') if task.evaluation_public else None
	}
