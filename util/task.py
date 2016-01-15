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

# Vraci dvojici { task_id : module_cnt } pro vsechny plne odevzdane ulohy
# sum(body) je suma bodu za vsechny moduly v dane uloze
# Plne odevzdane moduly = bez autocorrect, nebo s autocorrect majici plny pocet bodu
# Moduly s maximem 0 bodu jsou bonusove a jsou vzdy fully_submitted (i pokud nebyly odevzdany)
def fully_submitted(user_id, year_id=None):
	if user_id is None:
		return []

	q = session.query(model.Task.id, func.count(distinct(model.Module.id)).label('modules'))
	if year_id is not None:
			q = q.join(model.Wave, model.Task.wave == model.Wave.id).filter(model.Wave.year == year_id)
	q = q.outerjoin(model.Module).group_by(model.Task.id)

	max_modules_count = { task.id: task.modules for task in q.filter(model.Module.bonus == False).all() }

	real_modules_count = { task.id: task.modules for task in q.join(model.Evaluation).filter(model.Evaluation.user == user_id, or_(model.Module.autocorrect != True, model.Module.max_points == model.Evaluation.points)).group_by(model.Task.id).all() }

	return { int(key): int(val) for key, val in real_modules_count.items() if max_modules_count[key] <= val }

# Vraci dvojici { model.Task : sum(body) } pro vsechny jakkoliv odevzdane ulohy
# sum(body) je suma bodu za vsechny moduly v dane uloze
def any_submitted(user_id, year_id):
	# Skore uivatele per modul
	per_module = session.query(model.Evaluation.module.label('module'), func.max(model.Evaluation.points).label('points')).\
		join(model.Module, model.Evaluation.module == model.Module.id).\
		join(model.Task, model.Task.id == model.Module.task).\
		filter(model.Evaluation.user == user_id).\
		group_by(model.Evaluation.module).subquery()

	# Skore per task
	return session.query(model.Task, func.sum(per_module.c.points).label("score")).\
		join(model.Module, model.Module.task == model.Task.id).\
		join(per_module, model.Module.id == per_module.c.module).\
		join(model.Wave, model.Wave.id == model.Task.wave).\
		filter(model.Wave.year == year_id).\
		group_by(model.Task).all()

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
		func.max(model.Evaluation.points).label('points'), model.Evaluation.evaluator.label('evaluator')).\
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

# vraci seznam id vsech opravenych uloh daneho uzivatele
# tzn. u uloh, ktere jsou odevzdavany opakovane (automaticky vyhodnocovane)
# vraci ulohu, pokud resitel udelal submit alespon jednoho (teoreticky spatneho) reseni
def corrected(user_id):
	return [ r for (r, ) in session.query(model.Task.id).\
		filter(model.Task.evaluation_public).\
		join(model.Module, model.Module.task == model.Task.id).\
		join(model.Evaluation, model.Evaluation.module == model.Module.id).\
		filter(model.Evaluation.user == user_id).\
		group_by(model.Task).all() ]

def comment_thread(task_id, user_id):
	query = session.query(model.SolutionComment).filter(model.SolutionComment.task == task_id, model.SolutionComment.user == user_id).first()

	return query.thread if query is not None else None

# Vraci seznam automaticky opravovanych uloh, ktere maji plny pocet bodu.
# Pokud uloha nema automaticky opravovane moduly, vrati ji taky.
def autocorrected_full(user_id):
	q = session.query(model.Task.id.label('task_id'), func.count(distinct(model.Module.id)).label('mod_cnt')).\
		join(model.Module, model.Module.task == model.Task.id).\
		filter(model.Module.bonus == False).group_by(model.Task)

	max_modules_count = q.subquery()

	real_modules_count = q.join(model.Evaluation, model.Evaluation.module == model.Module.id).filter(model.Evaluation.user == user_id, or_(model.Module.autocorrect != True, model.Module.max_points == model.Evaluation.points)).subquery()

	return [ r for (r, ) in session.query(model.Task.id).\
		join(max_modules_count, model.Task.id == max_modules_count.c.task_id).\
		join(real_modules_count, model.Task.id == real_modules_count.c.task_id).\
		filter(max_modules_count.c.mod_cnt == real_modules_count.c.mod_cnt).all() ]

# Argumenty None slouzi k tomu, aby se usetrily SQL pozadavky:
#  pri hromadnem ziskavani stavu je mozne je vyplnit a pocet SQL dotazu bude mensi
#  Pokud jsou None, potrebne informace se zjisti z databaze.
def status(task, user, adeadline=None, fsubmitted=None, wave=None, corr=None, acfull=None):
	if not wave:
		wave = session.query(model.Wave).get(task.wave)

	# pokud neni prihlasen zadny uzivatel, otevreme jen ulohu bez prerekvizit
	# = prvvni uloha
	if user is None or user.id is None:
		return TaskStatus.BASE if task.prerequisite is None and wave.public else TaskStatus.LOCKED

	# pokud uloha neni v otevrene vlne, je LOCKED
	# vyjimkou jsou uzivatele s rolemi 'org' a 'admin', tem se zobrazuji vsechny ulohu
	if not wave.public and not user.role in ('org', 'admin', 'tester'):
		return TaskStatus.LOCKED

	if corr is None: corr = task.id in corrected(user.id)
	if acfull is None: acfull = task.id in autocorrected_full(user.id)

	# Pokud je uloha opravena, je DONE.
	# Uloha neni DONE dokud nemaji vsechny automaticky opravovane moduly plny pocet bodu.
	if corr and acfull:
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
	return TaskStatus.BASE if util.PrerequisitiesEvaluator(task.prerequisite_obj, currently_active).evaluate() or user.role in ('org', 'admin', 'tester') else TaskStatus.LOCKED

def solution_public(status, task, user):
	return ((task.time_deadline) and (status == TaskStatus.DONE or task.time_deadline < datetime.datetime.utcnow())) or user.role in ('org', 'admin', 'tester')

def time_published(task_id):
	return session.query(model.Wave.time_published).\
		join(model.Task, model.Task.wave == model.Wave.id).\
		filter(model.Task.id == task_id).scalar()

def to_json(task, user=None, adeadline=None, fsubmitted=None, wave=None, corr=None, acfull=None):
	max_points = sum([ module.max_points for module in task.modules ])
	tstatus = status(task, user, adeadline, fsubmitted, wave, corr, acfull)
	pict_base = task.picture_base if task.picture_base is not None else "/taskContent/" + str(task.id) + "/icon/"

	if not wave:
		wave = session.query(model.Wave).get(task.wave)

	return {
		'id': task.id,
		'title': task.title,
		'author': task.author,
		'details': task.id,
		'intro': task.intro,
		'max_score': format(sum([ module.max_points for module in task.modules if not module.bonus ]), '.1f'),
		'time_published': wave.time_published.isoformat(),
		'time_deadline': task.time_deadline.isoformat() if task.time_deadline else None,
		'state': tstatus,
		'prerequisities': [] if not task.prerequisite_obj else util.prerequisite.to_json(task.prerequisite_obj),
		'picture_base': pict_base,
		'picture_suffix': '.svg',
		'wave': task.wave
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
		'score': format(best_score.sum, '.1f')
	}

def admin_to_json(task):
	return {
		'id': task.id,
		'title': task.title,
		'wave': task.wave,
		'author': task.author,
		'git_path': task.git_path,
		'git_branch': task.git_branch,
		'git_commit': task.git_commit,
		'deploy_date': task.deploy_date.isoformat() if task.deploy_date else None,
		'deploy_status': task.deploy_status
	}

