import os
from sqlalchemy import func

from db import session
import model

MAX_UPLOAD_FILE_SIZE = 20 * 10**6
MAX_UPLOAD_FILE_COUNT = 20

def get(key):
	return session.query(model.Config).get(key).value

def ksi_conf():
	return get("ksi_conf")

def karlik_img():
	return get("mail_sign")

def ksi_web():
	return get("web_url")

def mail_sender():
	return get("mail_sender")

def feedback():
	return [ r for r, in session.query(model.FeedbackRecipient.email).all() ]


