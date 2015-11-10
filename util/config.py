import os
from sqlalchemy import func

from db import session
import model

def ksi_mail():
	return session.query(model.Config).get("ksi_conf").value

def karlik_img():
	return session.query(model.Config).get("mail_sign").value

def ksi_web():
	return session.query(model.Config).get("web_url").value

def ksi_mail():
	return session.query(model.Config).get("mail_sender").value

def feedback():
	return [ r for r, in session.query(model.FeedbackRecipient.email).all() ]

