from db import session
import model
import util

class Achievement(object):

	def on_get(self, req, resp, id):
		user = req.context['user']
		achievement = session.query(model.Achievement).get(id)

		req.context['result'] = { 'achievement': util.achievement.to_json(achievement, user.id) }


class Achievements(object):

	def on_get(self, req, resp):
		user = req.context['user']
		achievements = session.query(model.Achievement).\
			filter(model.Achievement.year == req.context['year']).all()

		req.context['result'] = { 'achievements': [ util.achievement.to_json(achievement, user.id) for achievement in achievements ] }
