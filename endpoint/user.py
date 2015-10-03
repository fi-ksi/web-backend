import os
from sqlalchemy import func, distinct

from db import session
import model
import util

def _load_points_for_user(user_id):
	return session.query(model.Evaluation.module, func.max(model.Evaluation.points).label('points')).\
		filter(model.Evaluation.user == user_id).\
		group_by(model.Evaluation.module).all()

def get_overall_points(user_id):
	return sum([ item.points for item in _load_points_for_user(user_id) if item.points is not None ])

def _user_to_json(user):
	data = { 'id': user.id, 'first_name': user.first_name, 'last_name': user.last_name, 'profile_picture': util.user.get_profile_picture(user) }

	if user.role == 'participant':
		data['score'] =  get_overall_points(user.id)
		data['tasks_num'] = 16
		data['achievements'] = list(util.achievement.ids_set(user.achievements))
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
