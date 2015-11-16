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
	general = q.filter(model.UserAchievement.task_id == 0).all()

	# Achievementy propojene s ulohou filtrujeme.
	task = q.join(model.Task, model.Task.id == model.UserAchievement.task_id).\
		filter(model.Task.evaluation_public).\
		join(model.Wave, model.Wave.id == model.Task.wave).\
		filter(model.Wave.year == year_id).all()

	return general + task


def active_years(user_id):
	if user_id is None:
		return []

	a = session.query(model.Year.id). \
		join(model.Wave, model.Wave.year == model.Year.id).\
		join(model.Task, model.Task.wave == model.Wave.id).\
		join(model.Module, model.Module.task == model.Task.id).\
		join(model.Evaluation, model.Evaluation.module == model.Task.id).\
		filter(model.Evaluation.user == user_id).\
		group_by(model.Year).all()
	return a

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

def get_profile_picture(user):
        return PROFILE_PICTURE_URL % user.id if user.profile_picture and os.path.isfile(user.profile_picture) else None

def to_json(user, year_id):
        data = { 'id': user.id, 'first_name': user.first_name, 'last_name': user.last_name, 'profile_picture': get_profile_picture(user), 'gender': user.sex }

        # skryty resitel je pro potreby frontendu normalni resitel
        if user.role == 'participant_hidden':
            data['role'] = 'participant'
        else:
            data['role'] = user.role
        data['score'] =  sum_points(user.id, year_id)
        data['tasks_num'] = len(util.task.fully_submitted(user.id, year_id))
        data['achievements'] = list(util.achievement.ids_set(achievements(user.id, year_id)))

        if user.role == 'participant' or user.role == 'participant_hidden':
                profile = session.query(model.Profile).get(user.id)
                data['addr_country'] = profile.addr_country
                data['school_name'] = profile.school_name
                data['seasons'] = active_years(user.id)
        else:
                data['nick_name'] = user.nick_name
                data['tasks'] = [ task.id for task in user.tasks ]
                data['short_info'] = user.short_info

        return data
