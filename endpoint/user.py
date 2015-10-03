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


class User(object):

	def on_get(self, req, resp, id):
		user = session.query(model.User).get(id)

		req.context['result'] = { 'user': util.user.to_json(user) }


class Users(object):
	def on_get(self, req, resp):
		filter = req.get_param('filter')
		users = session.query(model.User)

		if filter == 'organisators':
			users = users.filter(model.User.role != 'participant')
		elif filter == 'participants':
			users = users.filter(model.User.role == 'participant')

		users = users.all()

		req.context['result'] = { "users": [ util.user.to_json(user) for user in users ] }
