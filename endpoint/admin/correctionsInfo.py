import falcon
from sqlalchemy import func

from db import session
import model
import util

class CorrectionsInfo(object):

	"""
	Specifikace GET pozadavku:
	prazdny pozadavek vracici ulohy, vlny a uzivatele pro vyplneni filtru opravovatka
	"""
	def on_get(self, req, resp):
		user = req.context['user']
		year = req.context['year']

		#if (not user.is_logged_in()) or (not user.is_org()):
		#	resp.status = falcon.HTTP_400
		#	return

		tasks = session.query(model.Task).\
			join(model.Wave, model.Wave.id == model.Task.wave).\
			filter(model.Wave.year == year).all()

		waves = session.query(model.Wave).\
			filter(model.Wave.year == year, model.Wave.public).\
			join(model.Task, model.Task.wave == model.Wave.id).all()

		users = session.query(model.User)
		users = set(util.user.active_in_year(users, year).all())
		users |= set(session.query(model.User).\
			join(model.Task, model.Task.author == model.User.id).all())

		req.context['result'] = {
			'correctionsInfos': [ util.correctionInfo.task_to_json(task) for task in tasks ],
			'waves': [ util.wave.to_json(wave) for wave in waves ],
			'users': [ util.correctionInfo.user_to_json(user) for user in users ]
		}


