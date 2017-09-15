from db import session
import model
from util import config


def to_json(achievement):
    return {
        'id': achievement.id,
        'title': achievement.title,
        'active': True,
        'picture': achievement.picture,
        'description': achievement.description,
        'persistent': (achievement.year is None),
        'year': achievement.year
    }


def ids_set(achievements):
    return set([achievement.id for achievement in achievements])


def ids_list(achievements):
    return list(ids_set(achievements))


def per_task(user_id, task_id):
    return session.query(model.Achievement).\
        join(model.UserAchievement,
             model.UserAchievement.achievement_id == model.Achievement.id).\
        filter(model.UserAchievement.user_id == user_id,
               model.UserAchievement.task_id == task_id).all()
