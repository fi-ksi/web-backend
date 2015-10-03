import os
from sqlalchemy import func

from db import session
import model
import util

DEFAULT_PROFILE_PICTURE = '/img/avatar-default.svg'
PROFILE_PICTURE_URL = 'http://localhost:3000/images/profile/%d'

def points_per_task(user_id):
	tasks = session.query(model.Task)

	return { task: util.task.points(task.id, user_id) for task in tasks }

def sum_points(user_id):
	points = session.query(model.Evaluation.module, func.max(model.Evaluation.points).label('points')).\
		filter(model.Evaluation.user == user_id).group_by(model.Evaluation.module).all()

	return sum([ item.points for item in points if item.points is not None ])

def get_profile_picture(user):
	return PROFILE_PICTURE_URL % user.id if user.profile_picture and os.path.isfile(user.profile_picture) else DEFAULT_PROFILE_PICTURE

def to_json(user):
	data = { 'id': user.id, 'first_name': user.first_name, 'last_name': user.last_name, 'profile_picture': get_profile_picture(user) }

	if user.role == 'participant':
		data['score'] =  sum_points(user.id)
		data['tasks_num'] = 16
		data['achievements'] = list(util.achievement.ids_set(user.achievements))
	else:
		data['nick_name'] = user.nick_name
		data['tasks'] = [ task.id for task in user.tasks ]
		data['is_organisator'] = True
		data['short_info'] = user.short_info

	return data
