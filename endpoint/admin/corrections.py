import falcon
from sqlalchemy import func

from db import session
import model
import util
import datetime
import json

class Correction(object):
	# GET pozadavek na konkretni correction se spousti prevazne jako ospoved na POST
	# id je umele id, konstrukce viz util/correction.py
	def on_get(self, req, resp, id):
		user = req.context['user']
		year = req.context['year']
		task = int(id) / 100000
		participant = int(id) % 100000

		if (not user.is_logged_in()) or (not user.is_org()):
			resp.status = falcon.HTTP_400
			return

		# Ziskame prislusna 'evaluation's
		corrs = session.query(model.Evaluation, model.Task, model.Module).\
			filter(model.Evaluation.user == participant).\
			join(model.Module, model.Module.id == model.Evaluation.module).\
			join(model.Task, model.Task.id == model.Module.task).\
			join(model.Wave, model.Task.wave == model.Wave.id).\
			join(model.Year, model.Year.id == model.Wave.year).\
			filter(model.Year.id == year).\
			filter(model.Task.id == task)

		corr_task = corrs.group_by(model.Task).first()
		corr_modules = corrs.group_by(model.Module)

		req.context['result'] = {
			'correction': util.correction.to_json(corr_task, corr_modules)
		}

	# POST: propojeni diskuzniho vlakna komentare
	def _process_thread(self, corr):
		curr_thread = util.task.comment_thread(corr['task_id'], corr['user'])

		if (corr['comment'] is not None) and (curr_thread is None):
			# pridavame diskuzni vlakno
			comment = model.SolutionComment(thread=corr['comment'], user=corr['user'], task=corr['task_id'])
			session.add(comment)
			session.commit()
			session.close()

		if (corr['comment'] is None) and (curr_thread is not None):
			# mazeme diskuzni vlakno
			comment = session.query(model.SolutionComment).get((curr_thread, corr['user'], corr['task_id']))
			session.delete(comment)
			session.commit()

	# POST: pridavani a mazani achievementu
	def _process_achievements(self, corr):
		a_old = util.achievement.ids_list(util.achievement.per_task(corr['user'], corr['task_id']))
		a_new = corr['achievements']
		if a_old != a_new:
			# achievementy se nerovnaji -> proste smazeme vsechny dosavadni a pridame do db ty, ktere nam prisly
			for a_id in a_old:
				session.delete(session.query(model.UserAchievement).get(a_id))
				session.commit()

			for a_id in a_new:
				ua = UserAchievement(user_id=corr['user'], achievement_id=a_id, task_id=corr['task_id'])
				session.add(ua)
				session.commit()
				session.close()

	# POST: zpracovani hodnoceni modulu
	def _process_module(self, module, user_id):
		evaluation = session.query(model.Evaluation).get(module['eval_id'])
		if evaluation is None: return
		evaluation.points = module['points']
		evaluation.time = datetime.datetime.utcnow()
		evaluation.evaluator = user_id
		evaluation.full_report += str(datetime.datetime.utcnow()) + " Evaluating by org " + str(user_id) + " : " + str(module['points']) + " points" + '\n'
		session.commit()

	# POST ma stejne argumenty, jako GET
	def on_post(self, req, resp, id):
		user = req.context['user']

		if (not user.is_logged_in()) or (not user.is_org()):
			resp.status = falcon.HTTP_400
			return

		corr = json.loads(req.stream.read())['correction']

		self._process_thread(corr)
		self._process_achievements(corr)

		for module in corr['modules']:
			self._process_module(module, user.id)

		# odpovedi jsou updatnute udaje
		self.on_get(req, resp, id)

###############################################################################

class Corrections(object):

	"""
	Specifikace GET pozadavku:
	musi byt vyplnen alespon jeden z argumentu:
	?task=task_id
	?participant=user_id
	"""
	def on_get(self, req, resp):
		user = req.context['user']
		year = req.context['year']
		task = req.get_param_as_int('task')
		participant = req.get_param_as_int('participant')

		if task is None and participant is None:
			resp.status = falcon.HTTP_400
			return

		if (not user.is_logged_in()) or (not user.is_org()):
			resp.status = falcon.HTTP_400
			return

		# Ziskame prislusna 'evaluation's
		corrs = session.query(model.Evaluation, model.Task, model.Module)
		if participant is not None:
			corrs = corrs.filter(model.Evaluation.user == participant)
		corrs = corrs.join(model.Module, model.Module.id == model.Evaluation.module).\
			join(model.Task, model.Task.id == model.Module.task).\
			join(model.Wave, model.Task.wave == model.Wave.id).\
			join(model.Year, model.Year.id == model.Wave.year).\
			filter(model.Year.id == year)
		if task is not None:
			corrs = corrs.filter(model.Task.id == task)

		corrs_tasks = corrs.group_by(model.Task, model.Evaluation.user).all()
		corrs_modules = corrs.group_by(model.Module)

		achievements = session.query(model.Achievement).\
			filter(model.Achievement.year == req.context['year']).all()

		req.context['result'] = {
			'corrections': [ util.correction.to_json(corr, corrs_modules.filter(model.Task.id == corr.Task.id)) for corr in corrs_tasks ],
			'tasks': [ util.correction.task_to_json(q.Task) for q in corrs.group_by(model.Task).all() ],
			'modules': [ util.correction.module_to_json(q.Module) for q in corrs_modules.all() ],
			'achievements': [ util.achievement.to_json(achievement, user.id) for achievement in achievements ]
		}

