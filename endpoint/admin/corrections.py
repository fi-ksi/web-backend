import falcon
from sqlalchemy import func

from db import session
import model
import util

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
		task = req.get_param('task')
		participant = req.get_param('participant')

		if task is None and participant is None:
			resp.status = falcon.HTTP_400
			return

		#if (not user.is_logged_in()) or (not user.is_org()):
		#	resp.status = falcon.HTTP_400
		#	return

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

		req.context['result'] = {
			'corrections': [ util.correction.to_json(corr, corrs_modules.filter(model.Task.id == corr.Task.id)) for corr in corrs_tasks ],
			'tasks': [ util.correction.task_to_json(q.Task) for q in corrs.group_by(model.Task).all() ],
			'modules': [ util.correction.module_to_json(q.Module) for q in corrs_modules.all() ]
		}


class AdminCorrectingTask(object):
	def on_get(self, req, resp, id):
		pass

