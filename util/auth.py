from db import session
import model
import datetime

class UserInfo:

	def __init__(self, user=None, token=None):
		self.id = user.id if user else None
		self.role = user.role if user else None
		self.token = token

	def is_logged_in(self):
		return self.id is not None

	def get_id(self):
		return self.id

	def is_admin(self):
		return self.role == 'admin'

	def is_org(self):
		return self.role == 'org'


def update_tokens():
	tokens = session.query(model.Token).all()
	tokens = filter(lambda token: datetime.datetime.utcnow() > token.granted+(token.expire*2), tokens)
	for token in tokens:
		session.delete(token)
	session.commit()
