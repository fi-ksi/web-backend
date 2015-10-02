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

		req.context['result'] = { 'resultScores': [ util.score.user_to_json(user) for user in users ] }