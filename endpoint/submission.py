from db import session
import model

def _submission_to_json(submission):
	return { 'id': submission.id, 'datetime': submission.time.isoformat(), 'files': [], 'achievements': [],
		'score': sum([ evaluation.points for evaluation in submission.evaluations ]) }

class Submission(object):

	def on_get(self, req, resp, id):
		submission = session.query(model.Submission).get(id)

		req.context['result'] = { 'submission': _submission_to_json(submission) }

