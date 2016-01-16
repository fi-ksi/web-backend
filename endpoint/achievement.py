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

	def on_delete(self, req, resp, id):
		user = req.context['user']
		achievement = session.query(model.Achievement).get(id)

		if (not user.is_logged_in()) or (not user.is_admin()):
			resp.status = falcon.HTTP_400
			return

		if not achievement:
			resp.status = falcon.HTTP_404
			return

		# Ziskame vsechna prideleni daneho achievementu
		user_achs = session.query(model.UserAchievement).\
			filter(model.UserAchievement.achievement_id == id).all()

		try:
				for user_ach in user_achs:
					session.delete(user_ach)
				session.delete(achievement)
				session.commit()
		except:
				session.rollback()
				raise
		finally:
				session.close()

		req.context['result'] = {}


class Achievements(object):

	def on_get(self, req, resp):
		achievements = session.query(model.Achievement).\
			filter(model.Achievement.year == req.context['year']).all()

		req.context['result'] = { 'achievements': [ util.achievement.to_json(achievement) for achievement in achievements ] }
