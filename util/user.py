import os
from sqlalchemy import func

from db import session
import model
import util

PROFILE_PICTURE_URL = '/images/profile/%d'

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

        data['role'] = user.role

        if user.role == 'participant':
                data['score'] =  sum_points(user.id, year_id)
                data['tasks_num'] = len(util.task.fully_submitted(user.id, year_id))
                data['achievements'] = list(util.achievement.ids_set(filter(lambda a: a.year == year_id, user.achievements)))

                profile = session.query(model.Profile).get(user.id)
                data['addr_country'] = profile.addr_country
                data['school_name'] = profile.school_name
                data['seasons'] = active_years(user.id)
        else:
                data['nick_name'] = user.nick_name
                data['tasks'] = [ task.id for task in user.tasks ]
                data['short_info'] = user.short_info

        return data
