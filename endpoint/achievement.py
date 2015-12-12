from db import session
import model
import util
import falcon

class Achievement(object):

	def on_get(self, req, resp, id):
		achievement = session.query(model.Achievement).get(id)

		if achievement is None:
			resp.status = falcon.HTTP_404
			return

		req.context['result'] = { 'achievement': util.achievement.to_json(achievement) }


class Achievements(object):

	def on_get(self, req, resp):
		achievements = session.query(model.Achievement).\
			filter(model.Achievement.year == req.context['year']).all()

		req.context['result'] = { 'achievements': [ util.achievement.to_json(achievement) for achievement in achievements ] }
