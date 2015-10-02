from db import session
import model
import util

class Achievement(object):

	def on_get(self, req, resp, id):
		achievement = session.query(model.Achievement).get(id)

		req.context['result'] = { 'achievement': util.achievement.to_json(achievement) }


class Achievements(object):

	def on_get(self, req, resp):
		achievements = session.query(model.Achievement).all()

		req.context['result'] = { 'achievements': [ util.achievement.to_json(achievement) for achievement in achievements ] }
