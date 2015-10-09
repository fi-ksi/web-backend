import os
import falcon
import json
from sqlalchemy import func, distinct

from db import session
import model
import util
import auth

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
		users_json = [ util.user.to_json(user) for user in users ]

		if filter == 'participants':
			users_json = sorted(users_json, key=lambda user: user['score'], reverse=True)

		req.context['result'] = { "users": users_json }


class ChangePassword(object):

	def on_post(self, req, resp):
		user = req.context['user']

		if not user.is_logged_in():
			resp.status = falcon.HTTP_400
			return

		user = session.query(model.User).get(user.id)
		data = json.loads(req.stream.read())

		if not auth.check_password(data['old_password'], user.password):
			resp.status = falcon.HTTP_401
			req.context['result'] = { 'result': 'error' }
			return

		if data['new_password'] != data['new_password2']:
			req.context['result'] = { 'result': 'error' }
			return

		user.password = auth.get_hashed_password(data['new_password'])

		session.add(user)
		session.commit()
		session.close()

		req.context['result'] = { 'result': 'ok' }
