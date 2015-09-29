import os
from sqlalchemy import func, distinct

from db import session
import model
from achievement import achievements_ids

DEFAULT_PROFILE_PICTURE = '/img/avatar-default.svg'
PROFILE_PICTURE_URL = 'http://localhost:3000/images/profile/%d'

def _load_points_for_user(user_id):
	return session.query(model.Evaluation.module, func.max(model.Evaluation.points).label('points')).\
		filter(model.Evaluation.user == user_id).\
		group_by(model.Evaluation.module).all()

def get_overall_points(user_id):
	return sum([ item.points for item in _load_points_for_user(user_id) ])


def get_profile_picture(user):
	return PROFILE_PICTURE_URL % user.id if user.profile_picture and os.path.isfile(user.profile_picture) else DEFAULT_PROFILE_PICTURE,

def _user_to_json(user):
	data = { 'id': user.id, 'first_name': user.first_name, 'last_name': user.last_name, 'profile_picture': get_profile_picture(user) }

	if user.role == 'participant':
		data['score'] =  get_overall_points(user.id)
		data['tasks_num'] = 16
		data['achievements'] = achievements_ids(user.achievements)
	else:
		data['nick_name'] = user.nick_name
		data['tasks'] = [ task.id for task in user.tasks ]
		data['is_organisator'] = True
		data['short_info'] = user.short_info

	return data


class User(object):

	def on_get(self, req, resp, id):
		user = session.query(model.User).get(id)

		req.context['result'] = { 'user': _user_to_json(user) }


class Users(object):
	def on_get(self, req, resp):
		filter = req.get_param('filter')
		users = session.query(model.User)

		if filter == 'organisators':
			users = users.filter(model.User.role != 'participant')
		elif filter == 'participants':
			users = users.filter(model.User.role == 'participant')

		users = users.all()

		req.context['result'] = { "users": [ _user_to_json(user) for user in users ] }
