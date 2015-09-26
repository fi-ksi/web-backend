from db import session
import model

def achievements_ids(achievements):
	return [ achievement.id for achievement in achievements ]

def _achievement_to_json(achievement):
	return { 'id': achievement.id, 'title': achievement.title, 'active': True, 'picture_active': 'img/achievements/' + achievement.code + '.svg' }

class Achievement(object):

	def on_get(self, req, resp, id):
		achievement = session.query(model.Achievement).get(id)

		req.context['result'] = { 'achievement': _achievement_to_json(achievement) }


class Achievements(object):

	def on_get(self, req, resp):
		achievements = session.query(model.Achievement).all()

		req.context['result'] = { 'achievements': [ _achievement_to_json(achievement) for achievement in achievements ] }
