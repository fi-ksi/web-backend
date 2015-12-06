import falcon
from sqlalchemy import func

from db import session
import model
import util

class Email(object):

	# TODO:
	"""
	Specifikace POST pozadavku:
	{
		"Subject": String
		"Body": String,
		"From": String,
		"Sender": String,
		"Reply-To": String,
		"To": String,
		"Bcc": [String],
		"Gender": (both|male|female),
		"Users": (orgs, participants)
	}
	"""
	def on_post(self, req, resp, id):
		user = req.context['user']

		if (not user.is_logged_in()) or (not user.is_org()):
			resp.status = falcon.HTTP_400
			return


