# -*- coding: utf-8 -*-

from db import session
import model
import datetime

class UserInfo:

	def __init__(self, user=None, token=None):
		self.id = user.id if user else None
		self.role = user.role if user else None
		self.token = token
		self.user = user

	def is_logged_in(self):
		return self.id is not None

	def get_id(self):
		return self.id

	def is_admin(self):
		return self.role == 'admin'

	def is_org(self):
		return self.role == 'org' or self.role == 'admin'

	def is_tester(self):
		return self.role == 'tester'


def update_tokens():
	try:
		tokens = session.query(model.Token).all()
		tokens = filter(lambda token: datetime.datetime.utcnow() > token.expire, tokens)
		for token in tokens:
			session.delete(token)
		session.commit()
	except:
		session.rollback()
		raise
