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
