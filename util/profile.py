from math import floor

from db import session
import model
import util


def fake_profile():
    return {'profile': {'id': 0, 'signed_in': False}}


def to_json(user, profile, notify, year_obj, basic=False, sensitive: bool = False):
    """
    :param user:
    :param profile:
    :param notify:
    :param year_obj:
    :param basic:
    :param sensitive: it True, include sensitive information like user's address
    :return:
    """
    if basic:
        return {'profile': _basic_profile_to_json(user)}
    else:
        task_scores = {task: (points, wave, prereq) for task, points, wave,
                       prereq in util.task.any_submitted(user.id, year_obj.id)}

        adeadline = util.task.after_deadline()
        fsubmitted = util.task.fully_submitted(user.id, year_obj.id)
        corrected = util.task.corrected(user.id)
        autocorrected_full = util.task.autocorrected_full(user.id)
        task_max_points_dict = util.task.max_points_dict()

        # task_achievements je seznam [(Task,Achievement)] pro vsechny
        # achievementy uzivatele user v uloze Task
        task_achievements = session.query(model.Task, model.Achievement).\
            join(model.UserAchievement,
                 model.UserAchievement.task_id == model.Task.id).\
            join(model.Achievement,
                 model.UserAchievement.achievement_id ==
                 model.Achievement.id).\
            filter(model.UserAchievement.user_id == user.id,
                   model.Achievement.year == year_obj.id).\
            group_by(model.Task, model.Achievement).\
            all()

        return {
            'profile': dict(
                list(_basic_profile_to_json(user).items()) +
                list(_full_profile_to_json(user, profile, notify, task_scores,
                                           year_obj, sensitive=sensitive).items())
            ),
            'tasks': [
                util.task.to_json(
                    task, prereq, user, adeadline, fsubmitted, wave,
                    task.id in corrected, task.id in autocorrected_full,
                    task_max_points=task_max_points_dict[task.id])
                for task, (points, wave, prereq) in list(task_scores.items())
            ],
            'taskScores': [
                task_score_to_json(
                    task, points, user,
                    [ach.id for (_, ach) in
                        [tsk_ach for tsk_ach in task_achievements
                            if tsk_ach[0].id == task.id]]
                )
                for task, (points, _, _) in list(task_scores.items())
            ]
        }


def _basic_profile_to_json(user: model.User) -> dict:
    return {
        'id': user.id,
        'signed_in': True,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'nick_name': user.nick_name,
        'profile_picture': util.user.get_profile_picture(user),
        'short_info': user.short_info,
        'email': user.email,
        'gender': user.sex,
        'role': user.role,
        'github': user.github
    }


def _full_profile_to_json(user, profile, notify, task_scores, year_obj, sensitive: bool = False):
    """

    :param user:
    :param profile:
    :param notify:
    :param task_scores:
    :param year_obj:
    :param sensitive: it True, include sensitive information like user's address
    :return:
    """
    points, cheat = util.user.sum_points(user.id, year_obj.id)
    summary = max(util.task.sum_points(
        year_obj.id, bonus=False),
        year_obj.point_pad
    )
    successful = format(floor((float(points) / summary) *
                              1000) / 10, '.1f') if summary != 0 else 0

    data = {
        'addr_country': profile.addr_country,
        'school_name': profile.school_name,
        'school_street': profile.school_street,
        'school_city': profile.school_city,
        'school_zip': profile.school_zip,
        'school_country': profile.school_country,
        'school_finish': profile.school_finish,
        'tshirt_size': profile.tshirt_size,
        'achievements': list(util.achievement.ids_set(
            util.user.achievements(user.id, year_obj.id)
        )),
        'percentile': util.user.percentile(user.id, year_obj.id),
        'score': float(format(points, '.1f')),
        'seasons': [key for (key,) in util.user.active_years(user.id)],
        'percent': successful,
        'results': [task.id for task in list(task_scores.keys())],
        'tasks_num': len(util.task.fully_submitted(user.id, year_obj.id)),

        'notify_eval': notify.notify_eval if notify else True,
        'notify_response': notify.notify_response if notify else True,
        'notify_ksi': notify.notify_ksi if notify else True,
        'notify_events': notify.notify_events if notify else True,
        'cheat': cheat,
        'discord': user.discord
    }

    if sensitive:
        data.update({
            'addr_street': profile.addr_street,
            'addr_city': profile.addr_city,
            'addr_zip': profile.addr_zip,
        })
    return data

# \achievements ocekava seznam ID achievementu nebo None


def task_score_to_json(task, points, user, achievements=None):
    if achievements is None:
        achievements = [
            achievement.achievement_id
            for achievement in
            session.query(model.UserAchievement).
            filter(model.UserAchievement.user_id == user.id,
                   model.UserAchievement.task_id == task.id).
            all()
        ]

    return {
        'id': task.id,
        'task': task.id,
        'achievements': achievements,
        'score': float(format(points, '.1f')) if task.evaluation_public
        else None
    }
