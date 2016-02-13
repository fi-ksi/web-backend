from db import session
import model, util, falcon, json
from sqlalchemy import or_

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

	# UPDATE trofeje
	def on_put(self, req, resp, id):
		user = req.context['user']

		# Upravovat trofeje mohou jen orgove
		if (not user.is_logged_in()) or (not user.is_org()):
				resp.status = falcon.HTTP_400
				return

		data = json.loads(req.stream.read())['achievement']

		achievement = session.query(model.Achievement).get(id)
		if achievement is None:
			resp.status = falcon.HTTP_404
			return

		achievement.title = data['title']
		achievement.picture = data['picture']
		achievement.description = data['description']
		if not data['persistent']: achievement.year = req.context['year']
		else: achievement.year = None

		try:
			session.commit()
		except:
			session.rollback()
			raise
		finally:
			session.close()

		self.on_get(req, resp, id)

	# Smazani trofeje
	def on_delete(self, req, resp, id):
		user = req.context['user']

		if (not user.is_logged_in()) or (not user.is_org()):
			resp.status = falcon.HTTP_400
			return

		achievement = session.query(model.Achievement).get(id)
		if achievement is None:
			resp.status = falcon.HTTP_404
			return

		try:
			session.delete(achievement)
			session.commit()
			req.context['result'] = {}
		except:
			session.rollback()
			raise
		finally:
			session.close()


class Achievements(object):

	def on_get(self, req, resp):
		achievements = session.query(model.Achievement).\
			filter(or_(model.Achievement.year == None, model.Achievement.year == req.context['year'])).all()

		req.context['result'] = { 'achievements': [ util.achievement.to_json(achievement) for achievement in achievements ] }

	# Vytvoreni nove trofeje
	def on_post(self, req, resp):
		user = req.context['user']

		# Vytvoret novou trofej mohou jen orgove
		if (not user.is_logged_in()) or (not user.is_org()):
			resp.status = falcon.HTTP_400
			return

		data = json.loads(req.stream.read())['achievement']

		achievement = model.Achievement(
			title = data['title'],
			picture = data['picture'],
			description = data['description'],
		)
		if not data['persistent']: achievement.year = req.context['year']
		else: achievement.year = None

		try:
			session.add(achievement)
			session.commit()
		except:
			session.rollback()
			raise

		req.context['result'] = { 'achievement': util.achievement.to_json(achievement) }

		session.close()

