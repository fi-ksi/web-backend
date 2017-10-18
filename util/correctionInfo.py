import datetime
from sqlalchemy import func, distinct, or_, and_, not_, desc
from sqlalchemy.dialects import mysql

from db import session
import model
import util


def user_to_json(user):
    return {
        'id': user.id,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'role': user.role,
        'profile_picture': util.user.get_profile_picture(user),
        'gender': user.sex
    }


def _task_corr_state(task, evaluating=None):
    if task.evaluation_public:
        return "published"
    if task.id in util.correction.tasks_corrected():
        return "corrected"

    if evaluating is None:
        evaluating = session.query(model.Evaluation).\
            filter(model.Evaluation.evaluator != None).\
            join(model.Module, model.Module.id == model.Evaluation.module).\
            filter(model.Module.task == task.id).count() > 0

    return 'working' if evaluating else 'base'


def task_to_json(task, solvers=None, evaluating=None):
    if solvers is None:
        q = session.query(model.User.id).\
            join(model.Evaluation, model.Evaluation.user == model.User.id).\
            join(model.Module, model.Module.id == model.Evaluation.module).\
            filter(model.Module.task == task.id).group_by(model.User).all()
        solvers = [r for (r, ) in q]

    return {
        'id': task.id,
        'title': task.title,
        'wave': task.wave,
        'author': task.author,
        'corr_state': _task_corr_state(task, evaluating),
        'solvers': solvers
    }
