import os
from sqlalchemy import func, or_

from db import session
import model
import util

PROFILE_PICTURE_URL = '/images/profile/%d'


def achievements(user_id, year_id):
    """Vrati achievementy uzivatele.
    Achievementy v rocniku se vraci jen v rocniku, globalni achievementy se
    vraci ve vsech rocnicich.
    """
    return session.query(model.Achievement).\
        join(model.UserAchievement,
             model.UserAchievement.achievement_id == model.Achievement.id).\
        filter(model.UserAchievement.user_id == user_id).\
        filter(or_(model.Achievement.year == None,
                   model.Achievement.year == year_id)).\
        all()


def active_years(user_id):
    """Vraci [(year_id)] pro vsechny roky, v nichz je aktivni uzivatel
    'user_id'
    """
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


def active_years_all():
    """Vraci [(user,year)] pro vsechny roky v nichz je aktivni uzivatel user"""
    return session.query(model.User, model.Year).\
        join(model.Evaluation, model.Evaluation.user == model.User.id).\
        join(model.Module, model.Module.id == model.Evaluation.module).\
        join(model.Task, model.Task.id == model.Module.task).\
        join(model.Wave, model.Wave.id == model.Task.wave).\
        join(model.Year, model.Wave.year == model.Year.id).\
        group_by(model.User, model.Year).all()


def active_in_year(query, year_id):
    """predpoklada query, ve kterem se vyskytuje model User
    pozadavek profiltruje na ty uzivatele, kteri jsou aktivni v roce 'year'_id
    """
    return query.join(model.Evaluation,
                      model.Evaluation.user == model.User.id).\
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


def sum_points(user_id, year_id) -> (int, bool):
    """Returns (points, cheating)."""
    evals = session.query(
        func.max(model.Evaluation.points).label('points'),
        func.max(model.Evaluation.cheat).label('cheat'),
    ).\
        filter(model.Evaluation.user == user_id).\
        join(model.Module, model.Evaluation.module == model.Module.id).\
        join(model.Task, model.Task.id == model.Module.task).\
        filter(model.Task.evaluation_public).\
        join(model.Wave, model.Wave.id == model.Task.wave).\
        filter(model.Wave.year == year_id).\
        group_by(model.Evaluation.module).all()

    return (
        sum([points for points, _ in evals if points is not None]),
        any(cheat for _, cheat in evals),
    )


def percentile(user_id, year_id):
    upoints = {
        userid: points
        for userid, points in user_points(year_id).items()
        if points > 0
    }
    if user_id not in upoints:
        return 0

    points_order = sorted(list(upoints.values()), reverse=True)

    rank = 0
    for points in points_order:
        if points == upoints[user_id]:
            return round((1 - (rank / len(points_order))) * 100)
        rank += 1

    return 0


def points_per_module_subq(year_id):
    return session.query(model.User.id.label('user'),
                         model.Evaluation.module.label('module'),
                         func.max(model.Evaluation.points).label('points'),
                         func.max(model.Evaluation.cheat).label('cheat')).\
        join(model.Evaluation, model.Evaluation.user == model.User.id).\
        join(model.Module, model.Evaluation.module == model.Module.id).\
        join(model.Task, model.Task.id == model.Module.task).\
        filter(model.Task.evaluation_public).\
        join(model.Wave, model.Wave.id == model.Task.wave).\
        filter(model.Wave.year == year_id).\
        group_by(model.User.id, model.Evaluation.module).subquery()


def user_points(year_id):
    """Returns {user.id: user.points}."""
    points_per_module = points_per_module_subq(year_id)
    results = session.query(model.User.id,
                            func.sum(points_per_module.c.points).
                            label('sum_points'))

    results = results.join(points_per_module,
                           points_per_module.c.user == model.User.id).\
            group_by(model.User).all()

    return {userid: points for userid, points in results}


def successful_participants(year_obj):
    """vraci seznam [(user,points)] uspesnych v danem rocniku"""

    points_per_module = points_per_module_subq(year_obj.id)

    results = session.query(
        model.User,
        func.sum(points_per_module.c.points).label('sum_points'),
        func.max(points_per_module.c.cheat).label('cheat'),
    ).\
        join(points_per_module, points_per_module.c.user == model.User.id).\
        filter(model.User.role == 'participant').\
        group_by(model.User).all()

    max_points = util.task.sum_points(year_obj.id, bonus=False) + \
        year_obj.point_pad

    return [
        (user, points)
        for user, points, cheat in results
        if points >= 0.6*max_points and not cheat
    ]


def get_profile_picture(user):
    return (PROFILE_PICTURE_URL % (user.id)
        if user.profile_picture and os.path.isfile(user.profile_picture)
        else None)


def to_json(user, year_obj, total_score=None, tasks_cnt=None, profile=None,
            achs=None, seasons=None, users_tasks=None, admin_data=False,
            org_seasons=None, max_points=None, users_co_tasks=None,
            cheat=None):
    """Spoustu atributu pro serializaci lze teto funkci predat za ucelem
    minimalizace SQL dotazu. Toho se vyuziva napriklad pri vypisovani
    vysledkovky.
    Pokud jsou tyto atributy None, provedou se klasicke dotazy.
    'users_tasks' je [model.Task]
    'users'_co_tasks je [model.Task]
    """

    data = {
        'id': user.id,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'profile_picture': get_profile_picture(user),
        'gender': user.sex
    }

    if admin_data:
        data['email'] = user.email

    # skryty resitel je pro potreby frontendu normalni resitel
    if user.role == 'participant_hidden':
        data['role'] = 'participant'
    else:
        data['role'] = user.role

    if total_score is None or cheat is None:
        total_score, cheat = sum_points(user.id, year_obj.id)

    data['score'] = float(format(total_score, '.1f'))
    data['tasks_num'] = tasks_cnt if tasks_cnt is not None\
        else len(util.task.fully_submitted(user.id,
                                           year_obj.id))
    data['achievements'] = achs if achs is not None\
        else list(util.achievement.ids_set(achievements(user.id, year_obj.id)))
    data['enabled'] = user.enabled
    data['nick_name'] = user.nick_name

    if user.role == 'participant' or user.role == 'participant_hidden':
        if profile is None:
            profile = session.query(model.Profile).get(user.id)
        if max_points is None:
            max_points = util.task.sum_points(year_obj.id, bonus=False)\
                + year_obj.point_pad

        data['addr_country'] = profile.addr_country
        data['school_name'] = profile.school_name
        data['seasons'] = seasons if seasons is not None\
            else [key for (key,) in active_years(user.id)]
        data['successful'] = total_score >= (0.9 * max_points) and not cheat
        data['cheat'] = cheat

    elif user.role == 'org' or user.role == 'admin':
        if users_tasks is None:
            users_tasks = session.query(model.Task).\
                join(model.Wave, model.Wave.id == model.Task.wave).\
                filter(model.Task.author == user.id,
                       model.Wave.year == year_obj.id).\
                all()

        if users_co_tasks is None:
            users_co_tasks = session.query(model.Task).\
                join(model.Wave, model.Wave.id == model.Task.wave).\
                filter(model.Task.co_author == user.id,
                       model.Wave.year == year_obj.id).\
                all()

        data['tasks'] = [task.id for task in users_tasks]
        data['co_tasks'] = [task.id for task in users_co_tasks]
        data['short_info'] = user.short_info
        data['seasons'] = org_seasons if org_seasons is not None\
            else [key for (key,) in active_years_org(user.id)]

    elif user.role == 'tester':
        data['nick_name'] = user.nick_name
        data['short_info'] = user.short_info

    return data
