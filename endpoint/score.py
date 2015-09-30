from db import session
import model

import util.task

def _score_to_json(id, score):
	return { 'id': id, 'user': 1, 'task': id, 'reviewed_by': None, 'score': score, 'achievements': [] }

class Score(object):

	def on_get(self, req, resp, id):
		score = util.task.points(id, 1)

		req.context['result'] = { 'score': _score_to_json(id, score) }
