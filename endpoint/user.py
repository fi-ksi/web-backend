# -*- coding: utf-8 -*-
import os
import falcon
import json
import random, string
from sqlalchemy import func, distinct

from db import session
import model
import util
import auth

"""
def _load_points_for_user(user_id):
	return session.query(model.Evaluation.module, func.max(model.Evaluation.points).label('points')).\
		filter(model.Evaluation.user == user_id).\
		group_by(model.Evaluation.module).all()

def get_overall_points(user_id):
	return sum([ item.points for item in _load_points_for_user(user_id) if item.points is not None ])
"""

class User(object):

	def on_get(self, req, resp, id):
		user = session.query(model.User).get(id)

		req.context['result'] = { 'user': util.user.to_json(user, req.context['year']) }


class Users(object):
	def on_get(self, req, resp):
		filter = req.get_param('filter')
		sort = req.get_param('sort')

		per_user = session.query(model.Evaluation.user.label('user'), func.max(model.Evaluation.points).label('points')).\
			join(model.Module, model.Evaluation.module == model.Module.id).\
			join(model.Task, model.Task.id == model.Module.task).\
			filter(model.Task.evaluation_public).\
			join(model.Wave, model.Wave.id == model.Task.wave).\
			filter(model.Wave.year == req.context['year']).\
			group_by(model.Evaluation.user, model.Evaluation.module).subquery()

		users = session.query(model.User, func.sum(per_user.c.points).label("total_score")).join(per_user, model.User.id == per_user.c.user).group_by(model.User)

		if filter == 'organisators':
			users = users.filter(model.User.role == 'org')
		elif filter == 'participants':
			users = users.filter(model.User.role == 'participant')

		users = users.all()
		users_json = [ util.user.to_json(user.User, req.context['year'], user.total_score) for user in users if filter != 'participants' or util.user.any_task_submitted(user.User.id, req.context['year'])]

		if sort == 'score':
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

		try:
			session.add(user)
			session.commit()
		except:
			session.rollback()
			raise
		finally:
			session.close()

		req.context['result'] = { 'result': 'ok' }

class ForgottenPassword(object):

	def on_post(self, req, resp):
		email = json.loads(req.stream.read())['email']
		user = session.query(model.User).filter(model.User.email == email).first()

		if not user:
			resp.status = falcon.HTTP_400
			req.context['result'] = { 'result': 'error' }
			return

		new_password = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits + string.ascii_lowercase) for _ in range(8))

		user.password = auth.get_hashed_password(new_password)

		try:
			session.add(user)
			session.commit()
		except:
			session.rollback()
			raise

		util.mail.send([user.email], '[KSI] Nové heslo', u'Ahoj,<br/>na základě tvé žádosti ti bylo vygenerováno nové heslo: %s<br/><br/>KSI' % new_password)
		session.close()

		req.context['result'] = { 'result': 'ok' }
