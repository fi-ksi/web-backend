import os
from sqlalchemy import func

from db import session
import model

KSI_MAIL = session.query(model.Config).get("ksi_conf").value
KARLIK_IMG = session.query(model.Config).get("mail_sign").value
KSI_WEB = session.query(model.Config).get("web_url").value
KSI_MAIL = session.query(model.Config).get("mail_sender").value
FEEDBACK = [ r for r, in session.query(model.FeedbackRecipient.email).all() ]

