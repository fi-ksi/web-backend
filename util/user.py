# -*- coding: utf-8 -*-

import os
from sqlalchemy import func

from db import session
import model
import util

PROFILE_PICTURE_URL = '/images/profile/%d'

# Vrati achievementy uzivatele.
# Achievementy spojene s ulohami se vraci jen v rocniku, globalni achievementy se vraci ve vsech rocnicich.
def achievements(user_id, year_id):
	q = session.query(model.Achievement).\
		join(model.UserAchievement, model.UserAchievement.achievement_id == model.Achievement.id).\
		filter(model.UserAchievement.user_id == user_id)

	# Globalni achievementy nejsou propojeny s zadnou ulohou.
	general = q.filter(model.UserAchievement.task_id == None).all()

	# Achievementy propojene s ulohou filtrujeme.
	task = q.join(model.Task, model.Task.id == model.UserAchievement.task_id).\
		filter(model.Task.evaluation_public).\
		join(model.Wave, model.Wave.id == model.Task.wave).\
		filter(model.Wave.year == year_id).all()

	return general + task

# Vraci [(year_id)] pro vsechny roky, v nichz je aktivni uzivatel \user_id
def active_years(user_id):
	if user_id is None:
		return []

	a = session.query(model.Year.id). \
		join(model.Wave, model.Wave.year == model.Year.id).\
		join(model.Task, model.Task.wave == model.Wave.id).\
		join(model.Module, model.Module.task == model.Task.id).\
		join(model.Evaluation, model.Evaluation.module == model.Module.id).\
		filter(model.Evaluation.user == user_id).\
		group_by(model.Year).all()
	return a

def active_years_org(user_id):
	if user_id is None:
		return []

	a = session.query(model.Year.id). \
		join(model.ActiveOrg, model.ActiveOrg.year == model.Year.id).\
		filter(model.ActiveOrg.org == user_id).\
		group_by(model.Year).all()
	return a


# Vraci [(user,year)] pro vsechny roky v nichz je aktivni uzivatel user
def active_years_all():
	return session.query(model.User, model.Year).\
		join(model.Evaluation, model.Evaluation.user == model.User.id).\
		join(model.Module, model.Module.id == model.Evaluation.module).\
		join(model.Task, model.Task.id == model.Module.task).\
		join(model.Wave, model.Wave.id == model.Task.wave).\
		join(model.Year, model.Wave.year == model.Year.id).\
		group_by(model.User, model.Year).all()

# predpoklada query, ve kterem se vyskytuje model User
# pozadavek profiltruje na ty uzivatele, kteri jsou aktivni v roce \year_id
def active_in_year(query, year_id):
	return query.join(model.Evaluation, model.Evaluation.user == model.User.id).\
		join(model.Module, model.Module.id == model.Evaluation.module).\
		join(model.Task, model.Task.id == model.Module.task).\
		join(model.Wave, model.Wave.id == model.Task.wave).\
		filter(model.Wave.year == year_id)

def any_task_submitted(user_id, year_id):
	if user_id is None:
		return False

	return session.query(model.Evaluation). \
		join(model.Module, model.Module.id == model.Evaluation.module).\
		filter(model.Evaluation.user == user_id).\
		join(model.Task, model.Task.id == model.Module.task).\
		join(model.Wave, model.Wave.id == model.Task.wave).\
		filter(model.Wave.year == year_id).count() > 0

def points_per_task(user_id):
	tasks = session.query(model.Task)

	return { task: util.task.points(task.id, user_id) for task in tasks }

def sum_points(user_id, year_id):
	points = session.query(model.Evaluation.module, func.max(model.Evaluation.points).label('points')).\
		filter(model.Evaluation.user == user_id).\
		join(model.Module, model.Evaluation.module == model.Module.id).\
		join(model.Task, model.Task.id == model.Module.task).\
		filter(model.Task.evaluation_public).\
		join(model.Wave, model.Wave.id == model.Task.wave).\
		filter(model.Wave.year == year_id).\
		group_by(model.Evaluation.module).all()

	return sum([ item.points for item in points if item.points is not None ])

def percentile(user_id, year_id):
	query = session.query(model.User).filter(model.User.role == 'participant')
	count = query.count()
	user_points = { user.id: sum_points(user.id, year_id) for user in query.all() }
	points_order = sorted(user_points.values(), reverse=True)

	if user_id not in user_points:
		return 0

	rank = 0.0
	for points in points_order:
		if points == user_points[user_id]:
				return round((1 - (rank / count)) * 100)
		rank += 1

	return 0

# vraci seznam resitelu uspesnych v danem rocniku
def successful_participants(year_obj):
	max_points = util.task.sum_points(year_obj.id, bonus=False) + year_obj.point_pad
	points_per_module = session.query(model.User.id.label('user'), model.Evaluation.module, func.max(model.Evaluation.points).label('points')).\
		join(model.Evaluation, model.Evaluation.user == model.User.id).\
		join(model.Module, model.Evaluation.module == model.Module.id).\
		join(model.Task, model.Task.id == model.Module.task).\
		filter(model.Task.evaluation_public).\
		join(model.Wave, model.Wave.id == model.Task.wave).\
		filter(model.Wave.year == year_obj.id).\
		group_by(model.User.id, model.Evaluation.module).subquery()

	return session.query(model.User).\
		join(points_per_module, points_per_module.c.user == model.User.id).\
		filter(points_per_module.c.points >= 0.6*max_points).all()

def get_profile_picture(user):
	return PROFILE_PICTURE_URL % user.id if user.profile_picture and os.path.isfile(user.profile_picture) else None

# Spoustu atributu pro serializaci lze teto funkci predat za ucelem
# minimalizace SQL dotazu. Toho se vyuziva napriklad pri vypisovani vysledkovky.
# Pokud jsou tyto atributy None, provedou se klasicke dotazy.
# \users_tasks je [model.Task]
def to_json(user, year_obj, total_score=None, tasks_cnt=None, profile=None, achs=None, seasons=None, users_tasks=None, admin_data=False, org_seasons=None, max_points=None):
	data = { 'id': user.id, 'first_name': user.first_name, 'last_name': user.last_name, 'profile_picture': get_profile_picture(user), 'gender': user.sex }
	if admin_data: data['email'] = user.email

	# skryty resitel je pro potreby frontendu normalni resitel
	if user.role == 'participant_hidden':
		data['role'] = 'participant'
	else:
		data['role'] = user.role

	if total_score is None: total_score = sum_points(user.id, year_obj.id)

	data['score'] = float(format(total_score, '.1f'))
	data['tasks_num'] = tasks_cnt if tasks_cnt is not None else len(util.task.fully_submitted(user.id, year_obj.id))
	data['achievements'] = achs if achs is not None else list(util.achievement.ids_set(achievements(user.id, year_obj.id)))
	data['enabled'] = user.enabled
	data['nick_name'] = user.nick_name

	if user.role == 'participant' or user.role == 'participant_hidden':
		if profile is None: profile = session.query(model.Profile).get(user.id)
		if max_points is None: max_points = util.task.sum_points(year_obj.id, bonus=False) + year_obj.point_pad
		data['addr_country'] = profile.addr_country
		data['school_name'] = profile.school_name
		data['seasons'] = seasons if seasons is not None else [ key for (key,) in active_years(user.id) ]
		data['successful'] = total_score >= (0.6*max_points)
	elif user.role == 'org' or user.role == 'admin':
		if users_tasks is None:
			users_tasks = session.query(model.Task).\
				join(model.Wave, model.Wave.id == model.Task.wave).\
				filter(model.Task.author == user.id, model.Wave.year == year_obj.id).all()

		data['tasks'] = [ task.id for task in users_tasks ]
		data['short_info'] = user.short_info
		data['seasons'] = org_seasons if org_seasons is not None else [ key for (key,) in active_years_org(user.id) ]
	elif user.role == 'tester':
		data['nick_name'] = user.nick_name
		data['short_info'] = user.short_info

	return data
