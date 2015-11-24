import datetime
from sqlalchemy import func, distinct, or_, desc
from sqlalchemy.dialects import mysql

from db import session
import model
import util

class TaskStatus:
	LOCKED = 'locked'
	BASE = 'base'
	CORRECTING = 'correcting'
	DONE = 'done'

# Vraci dvojici { task_id : sum(body) } pro vsechny plne odevzdane moduly v uloze
# Plne odevzdane moduly = bez autocorrect, nebo s autocorrect majici plny pocet bodu
def fully_submitted(user_id, year_id=None):
	if user_id is None:
		return []

	q = session.query(model.Task.id, func.count(distinct(model.Module.id)).label('modules'))
	if year_id is not None:
			q = q.join(model.Wave, model.Task.wave == model.Wave.id).filter(model.Wave.year == year_id)
	q = q.outerjoin(model.Module).group_by(model.Task.id)

	max_modules_count = { task.id: task.modules for task in q.all() }

	real_modules_count = { task.id: task.modules for task in q.join(model.Evaluation).filter(model.Evaluation.user == user_id, or_(model.Module.autocorrect != True, model.Module.max_points == model.Evaluation.points)).group_by(model.Task.id).all() }

	return { int(key): int(val) for key, val in real_modules_count.items() if max_modules_count[key] == val }

def after_deadline():
	return { int(task.id) for task in session.query(model.Task).filter(model.Task.time_deadline < datetime.datetime.utcnow() ).all() }

def max_points(task_id):
	points = session.query(func.sum(model.Module.max_points).label('points')).\
		filter(model.Module.task == task_id).first().points

	return int(points) if points else 0

def max_points_dict():
	points_per_task = session.query(model.Module.task.label('id'), func.sum(model.Module.max_points).label('points')).\
		group_by(model.Module.task).all()

	return { task.id: int(task.points) for task in points_per_task }

def points_per_module(task_id, user_id):
	return session.query(model.Module, \
		func.max(model.Evaluation.points).label('points')).\
		join(model.Evaluation, model.Evaluation.module == model.Module.id).\
		filter(model.Module.task == task_id, model.Evaluation.user == user_id).\
		join(model.Task, model.Task.id == model.Module.task).\
		filter(model.Task.evaluation_public).\
		group_by(model.Evaluation.module).all()

def points(task_id, user_id):
	ppm = points_per_module(task_id, user_id)

	if len(ppm) == 0:
		return None

	return sum(module.points for module in ppm if module.points is not None)

# vraci, jestli je uloha opravena
# tzn. u uloh, ktere jsou odevzdavany opakovane (automaticky vyhodnocovane)
# vraci True, pokud resitel udela submit alespon jednoho (teoreticky spatneho) reseni
def corrected(task_id, user_id):
	return session.query(model.Evaluation).\
		join(model.Module, model.Evaluation.module == model.Module.id).\
		filter(model.Module.task == task_id, model.Evaluation.user == user_id).\
		join(model.Task, model.Task.id == model.Module.task).\
		filter(model.Task.evaluation_public).\
		group_by(model.Evaluation.module).count() > 0

def comment_thread(task_id, user_id):
	query = session.query(model.SolutionComment).filter(model.SolutionComment.task == task_id, model.SolutionComment.user == user_id).first()

	return query.thread if query is not None else None

# Vraci true, pokud maji vsechny automaticky opravovane moduly v uloze
# plny pocet bodu, jinak False
# Pokud uloha nema automaticky opravovane moduly, vraci True.
def autocorrected_full(task_id, user_id):
	q = session.query(model.Module).join(model.Task, model.Module.task == model.Task.id).filter(model.Task.id == task_id)
	
	max_modules_count = q.count()

	real_modules_count = q.join(model.Evaluation, model.Evaluation.module == model.Module.id).filter(model.Evaluation.user == user_id, or_(model.Module.autocorrect != True, model.Module.max_points == model.Evaluation.points)).group_by(model.Module).count()

	return max_modules_count == real_modules_count

def status(task, user, adeadline=None, fsubmitted=None):
	task_opened_in_wave =  session.query(model.Task).\
	join(model.Wave, model.Wave.id == model.Task.wave).\
	filter(model.Wave.public).all()

	# pokud neni prihlasen zadny uzivatel, otevreme jen ulohu bez prerekvizit
	# = prvvni uloha
	if user is None or user.id is None:
		return TaskStatus.BASE if task.prerequisite is None and task in task_opened_in_wave else TaskStatus.LOCKED

	# pokud uloha neni v otevrene vlne, je LOCKED
	# vyjimkou jsou uzivatele s rolemi 'org' a 'admin', tem se zobrazuji vsechny ulohu
	if not task in task_opened_in_wave and not user.role in ('org', 'admin'):
		return TaskStatus.LOCKED

	# Pokud je uloha opravena, je DONE.
	# Uloha neni DONE dokud nemaji vsechny automaticky orpavovane moduly plny pocet bodu.
	if corrected(task.id, user.id) and autocorrected_full(task.id, user.id):
		return TaskStatus.DONE

	if not fsubmitted:
		fsubmitted = fully_submitted(user.id)

	# Pokud je uloha odevzdana a jeste neopravena, je CORRECTING
	if task.id in fsubmitted:
		return TaskStatus.CORRECTING

	if not adeadline:
		adeadline = after_deadline()

	# pokud je po deadline, zadani ulohy se otevira vsem
	currently_active = adeadline | set(fully_submitted(user.id).keys())
	if task.id in currently_active:
		return TaskStatus.BASE

	# Pokud nenastal ani jeden z vyse zminenych pripadu, otevreme ulohu, pokud
	# jsou splneny prerekvizity
	return TaskStatus.BASE if util.PrerequisitiesEvaluator(task.prerequisite_obj, currently_active).evaluate() or user.role in ('org', 'admin') else TaskStatus.LOCKED

def solution_public(status, task, user):
	return status == TaskStatus.DONE or task.time_deadline < datetime.datetime.utcnow() or user.role in ('org', 'admin')

def time_published(task_id):
	return session.query(model.Wave.time_published).\
		join(model.Task, model.Task.wave == model.Wave.id).\
		filter(model.Task.id == task_id).scalar()

def to_json(task, user=None, adeadline=None, fsubmitted=None):
	max_points = sum([ module.max_points for module in task.modules ])
	tstatus = status(task, user, adeadline, fsubmitted)
	pict_base = task.picture_base if task.picture_base is not None else "/taskContent/" + str(task.id) + "/icon/"

	return {
		'id': task.id,
		'title': task.title,
		'author': task.author,
		'details': task.id,
		'intro': task.intro,
		'max_score': sum([ module.max_points for module in task.modules ]),
		'time_published': time_published(task.id).isoformat(),
		'time_deadline': task.time_deadline.isoformat(),
		'state': tstatus,
		'prerequisities': [] if not task.prerequisite_obj else util.prerequisite.to_json(task.prerequisite_obj),
		'picture_base': pict_base,
		'picture_suffix': '.svg'
	}

def details_to_json(task, user, status, achievements, best_scores, comment_thread=None):
	return {
		'id': task.id,
		'body': task.body,
		'thread': task.thread,
		'modules': [ module.id for module in task.modules ],
		'best_scores': [ best_score.User.id for best_score in best_scores ],
		'comment': comment_thread if task.evaluation_public else None,
		'solution': task.solution if solution_public(status, task, user) else None,
		'achievements': [ achievement.id for achievement in achievements ]
	}

def best_scores(task_id):
	per_modules = session.query(model.User.id.label('user_id'), \
			func.max(model.Evaluation.points).label('points')).\
			join(model.Evaluation, model.Evaluation.user == model.User.id).\
			filter(model.Module.task == task_id, 'points' is not None).\
			join(model.Module, model.Evaluation.module == model.Module.id).\
			join(model.Task, model.Task.id == model.Module.task).\
			filter(model.Task.evaluation_public).\
			group_by(model.Evaluation.module, model.User).subquery()

	return session.query(model.User, func.sum(per_modules.c.points).label('sum')).join(per_modules, per_modules.c.user_id == model.User.id).filter(model.User.role == 'participant').group_by(per_modules.c.user_id).order_by(desc('sum')).slice(0, 5).all()

def best_score_to_json(best_score):
	achievements = session.query(model.UserAchievement).filter(model.UserAchievement.user_id == best_score.User.id).all()

	return {
		'id': best_score.User.id,
		'user': best_score.User.id,
		'achievements': [ achievement.achievement_id for achievement in achievements ],
		'score': int(best_score.sum)
	}
