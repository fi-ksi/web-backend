# -*- coding: utf-8 -*-
import os
import falcon
import json
import random, string
from sqlalchemy import func, distinct, desc, text, or_

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

		if user is None:
			resp.status = falcon.HTTP_404
			return

		req.context['result'] = { 'user': util.user.to_json(user, req.context['year'], admin_data=req.context['user'].is_org()) }

	def on_delete(self, req, resp, id):
		user = req.context['user']
		user_db = session.query(model.User).get(id)

		if (not user.is_logged_in()) or (not user.is_admin()):
			resp.status = falcon.HTTP_400
			return

		if not user_db:
			resp.status = falcon.HTTP_404
			return

		profile = session.query(model.Profile).get(id)

		try:
			if profile: session.delete(profile)
			session.delete(user_db)
			session.commit()
		except:
			session.rollback()
			raise
		finally:
			session.close()

		req.context['result'] = {}


class Users(object):
	def on_get(self, req, resp):
		filt = req.get_param('filter')
		sort = req.get_param('sort')

		# Tady se dela spoustu magie kvuli tomu, aby se usetrily SQL dotazy
		# Snazime se minimalizovat pocet dotazu, ktere musi byt provedeny pro kadeho uzivatele
		# a misto toho provest pouze jeden MEGA dotaz.
		# Slouzi predevsim pro rychle nacitani vysledkove listiny.

		# Skore uzivatele per modul (zahrnuje jen moduly evaluation_public)
		per_user = session.query(model.Evaluation.user.label('user'), func.max(model.Evaluation.points).label('points')).\
			join(model.Module, model.Evaluation.module == model.Module.id).\
			join(model.Task, model.Task.id == model.Module.task).\
			filter(model.Task.evaluation_public).\
			join(model.Wave, model.Wave.id == model.Task.wave).\
			filter(model.Wave.year == req.context['year']).\
			group_by(model.Evaluation.user, model.Evaluation.module).subquery()

		# Pocet odevzdanych uloh (zahrnuje i module not evaluation_public i napriklad automaticky opravovane moduly s 0 body)
		tasks_per_user = session.query(model.Evaluation.user.label('user'), func.count(distinct(model.Task.id)).label('tasks_cnt')).\
			join(model.Module, model.Evaluation.module == model.Module.id).\
			join(model.Task, model.Task.id == model.Module.task).\
			join(model.Wave, model.Wave.id == model.Task.wave).\
			filter(model.Wave.year == req.context['year']).\
			group_by(model.Evaluation.user).subquery()

		# Ziskame vsechny uzivatele
		# Tem, kteri maji evaluations, je prirazen pocet bodu a pocet odevzdanych uloh
		# Vraci n tici: (model.User, total_score, tasks_cnt, model.Profile)
		# POZOR: outerjoin je dulezity, chceme vracet i uzivatele, kteri nemaji zadna evaluations (napriklad orgove pro seznam orgu)
		users = session.query(model.User, func.sum(per_user.c.points).label("total_score"), tasks_per_user.c.tasks_cnt.label('tasks_cnt'), model.Profile).\
			outerjoin(per_user, model.User.id == per_user.c.user).\
			outerjoin(tasks_per_user, model.User.id == tasks_per_user.c.user).\
			join(model.Profile, model.User.id == model.Profile.user_id).\
			group_by(model.User)

		# Filtrovani skupin uzivatelu
		if filt == 'organisators':
			users = users.filter(or_(model.User.role == 'org', model.User.role == 'admin'))
		elif filt == 'participants':
			# Resitele zobrazujeme jen v aktualnim rocniku (pro jine neni tasks_cnt definovano)
			users = users.filter(model.User.role == 'participant').\
				filter(text("tasks_cnt"), text("tasks_cnt") > 0)

		# Razeni uzivatelu
		if sort == 'score':
			users = users.order_by(desc("total_score"))

		# Polozime SQL dotaz a ziskame vsechny relevantni uzivatele
		users = users.all()

		# A ted prijdou na radu hratky a achievementy a aktivnimi rocniky: seznamy patrici kazdemu uzivateli
		# Samozrejme nechceme pro kazdeho uzivatele delat zvlastni dotaz.

		# Achievementy:
		achievements = session.query(model.User.id.label('user_id'), model.Achievement.id.label('a_id')).\
			join(model.UserAchievement, model.UserAchievement.user_id == model.User.id).\
			join(model.Achievement, model.Achievement.id == model.UserAchievement.achievement_id).\
			group_by(model.User, model.Achievement).all()

		# Aktivni roky:
		seasons = session.query(model.Year.id.label('year_id'), model.User.id.label('user_id')).\
			join(model.Wave, model.Wave.year == model.Year.id).\
			join(model.Task, model.Task.wave == model.Wave.id).\
			join(model.Module, model.Module.task == model.Task.id).\
			join(model.Evaluation, model.Evaluation.module == model.Module.id).\
			join(model.User, model.Evaluation.user == model.User.id).\
			group_by(model.User, model.Year).all()

		# Ziskani seznamu uloh vsech orgu na jeden dotaz
		if filt == 'organisators':
			users_tasks = session.query(model.User, model.Task).\
				join(model.Task, model.User.id == model.Task.author).\
				group_by(model.User, model.Task).all()
		else:
			users_tasks = None

		# Uzivatele s nedefinovanymi tasks_cnt v tomto rocniku  neodevzdali zadnou ulohu
		# -> nastavime jim natvrdo 'tasks_cnt' = 0 a total_score = 0, abychom omezili
		# dalsi SQL dotazy v util.user.to_json
		users_json = [ util.user.to_json(user.User, req.context['year'], \
			user.total_score if user.total_score else 0, \
			user.tasks_cnt if user.tasks_cnt else 0, \
			user.Profile, \
			[ item.a_id for item in achievements if item.user_id == user.User.id ], \
			[ item.year_id for item in seasons if item.user_id == user.User.id ], \
			[ task for (_, task) in filter(lambda (usr,task): usr.id == user.User.id, users_tasks) ] if users_tasks else None, \
			admin_data=req.context['user'].is_org() ) for user in users ]

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

		try:
			util.mail.send(user.email, '[KSI] Nové heslo', u'Ahoj,<br/>na základě tvé žádosti ti bylo vygenerováno nové heslo: %s<br/><br/>KSI' % new_password)
		except:
			e = sys.exc_info()[0]
			print str(e)
		session.close()

		req.context['result'] = { 'result': 'ok' }
