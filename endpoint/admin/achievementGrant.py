# -*- coding: utf-8 -*-

from db import session
import model, util, falcon, json, datetime

class AchievementGrant(object):

	"""
	Format dat:
	{
		"users": [ id ],
		"task": (null|id),
		"achievement": id
	}
	"""
	# Prideleni achievementu
	def on_post(self, req, resp):
		user = req.context['user']
		data = json.loads(req.stream.read())

		if (not user.is_logged_in()) or (not user.is_org()):
			resp.status = falcon.HTTP_400
			return

		try:
			for u in data['users']:
				if not data['task']: data['task'] = 0

				if not session.query(model.UserAchievement).get( (u, data['achievement'], data['task']) ):
					ua = model.UserAchievement(
						user_id = u,
						achievement_id = data['achievement'],
						task_id = data['task']
					)
					session.add(ua)

			session.commit()
			req.context['result'] = '{}'
		except:
			session.rollback()
			raise
		finally:
			session.close()

