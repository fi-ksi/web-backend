import falcon
from sqlalchemy import func

from db import session
import model
import util

class AdminCorrections(object):

	"""
	Specifikace GET pozadavku:
	musi byt vyplnen alespon jeden z argumentu:
	?task=task_id
	?participant=user_id
	"""
	def on_get(self, req, resp, id):
		user = req.context['user']
		year = req.context['year']
		task = req.get_param('task')
		participant = req.get_param('participant')

		#if (not user.is_logged_in()) or (not user.is_org()):
		#	resp.status = falcon.HTTP_400
		#	return

		# Ziskame prislusna 'evaluation's
		corrs = session.query(model.Evaluation, model.Task.label('task'), model.User.label('usr'))
		if participant is not None:
			corrs = corrs.filter(model.Evaluation.user == participant)
		corrs = corrs.join(model.Module, model.Module.id == model.Evaluation.module).\
			join(model.Task, model.Task.id == model.Module.task).\
			join(model.Wave, model.Task.wave == model.Wawe.id).\
			join(model.Year, model.Year.id == model.Wave.year).\
			filter(model.Year.id == year)
		if task is not None:
			corrs = corrs.filter(model.Task.id == task)

		corrs_tasks = corrs.group_by(model.Task, model.User).all()
		corrs_modules = corrs.group_by(model.Module)

		req.context['result'] = { 'corrections': [ util.task.to_json(corr, corrs_modules.filter(model.Task.id == corr.task.id).all()) for corr in corrs_tasks ] }


class AdminCorrectingTask(object):
	def on_get(self, req, resp, id):
		pass

