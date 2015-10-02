import util

def user_to_json(user):
	points = [ points for points in util.user.points_per_task(user.id).values() if points is not None ]

	return {
		'id': user.id,
		'user': user.id,
		'achievements': util.achievement.ids_list(user.achievements),
		'score': sum(points),
		'tasks_count': len(points)
	}