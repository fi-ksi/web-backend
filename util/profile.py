from db import session
import model
import util

def fake_profile():
	return { 'profile': { 'id': 0, 'signed_in': False } }

def to_json(user, profile):
	task_scores = { task: points for task, points in util.user.points_per_task(user.id).items() if points is not None }
	tasks = { task.id: task for task in session.query(model.Task) }

	return {
		'profile': [ _profile_to_json(user, profile, task_scores) ],
		'tasks': [ util.task.to_json(task) for task in task_scores.keys() ],
		'taskScores': [ task_score_to_json(task, points, user) for task, points in task_scores.items() ]
	}

def _profile_to_json(user, profile, task_scores):
	points = util.user.sum_points(user.id)
	summary = sum(util.task.max_points_dict().values())
	if summary == 0:
		successful = 0
	else:
		successful = round((float(points)/summary) * 100)

	return {
		'id': user.id,
		'signed_in': True,
		'first_name': user.first_name,
		'last_name': user.last_name,
		'profile_picture': util.user.get_profile_picture(user),
		'short_info': user.short_info,
		'email': user.email,
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
		'achievements': list(util.achievement.ids_set(user.achievements)),
		'percentile': util.user.percentile(user.id),
		'score': points,
		'seasons': 1,
		'successful': int(successful),
		'results': [ task.id for task in task_scores.keys() ]
	}


def task_score_to_json(task, points, user):
	return {
		'id': task.id,
		'task': task.id,
		'achievements': [ achievement.achievement_id for achievement in session.query(model.UserAchievement).filter(model.UserAchievement.user_id == user.id, model.UserAchievement.task_id == task.id).all()],
		'score': points
	}