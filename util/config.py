import os
from sqlalchemy import func

from db import session
import model

def get(key):
	return session.query(model.Config).get(key).value

def ksi_mail():
	return et("ksi_conf")

def karlik_img():
	return get("mail_sign")

def ksi_web():
	return get("web_url")

def ksi_mail():
	return get("mail_sender")

def feedback():
	return [ r for r, in session.query(model.FeedbackRecipient.email).all() ]


