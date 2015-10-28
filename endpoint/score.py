from db import session
import model

import util

def _score_to_json(id, score):
	return { 'id': id, 'user': 1, 'task': id, 'reviewed_by': None, 'score': score, 'achievements': [] }

class Score(object):

	def on_get(self, req, resp, id):
		score = util.task.points(id, 1)

		req.context['result'] = { 'score': _score_to_json(id, score) }


class ResultScores(object):

	def on_get(self, req, resp):
		users = session.query(model.User)

		ru = []
		for user in users:
			if (user.role == 'participant') and  (util.user.any_task_submitted(user.id, req.context['year'])):
				ru.append(util.user.to_json(user, req.context['year']))
		req.context['result'] = { 'resultScores': ru }

