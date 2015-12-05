import smtplib
from email.mime.text import MIMEText
from email import Charset
import sys

from db import session
import random
import model
from util import config

def easteregg():
	rand = random.randrange(0, session.query(model.MailEasterEgg).count())
	egg = session.query(model.MailEasterEgg).all()[rand]
	return u"<hr><p>PS: "  + egg.body + u"</p>"

def send(to, subject, text, params={}, bcc=[]):
	Charset.add_charset('utf-8', Charset.QP, Charset.QP, 'utf-8')
	text = u"<html>" + text + u"</html>"

	msg = MIMEText(text, 'html', 'utf-8')

	msg['Subject'] = subject
	msg['From'] = config.mail_sender()
	msg['To'] = (','.join(to)) if isinstance(to, (list)) else to
	msg['Return-Path'] = config.get('return_path')

	for key, value in params: msg[key] = params[value]

	try:
		s = smtplib.SMTP('relay.muni.cz')
		send_to = (to if isinstance(to, (list)) else [ to ]) + (bcc if isinstance(bcc, (list)) else [ bcc ])
		s.sendmail(msg['From'], send_to, msg.as_string())
		s.quit()
	except:
		e = sys.exc_info()[0]
		print str(e)

def send_multiple(to, subject, text, params={}, bcc=[]):
	send(bcc, subject, text, params)
	for recipient in to:
		send(recipient, subject, text, params)

def send_feedback(text, addr_from):
	addr_reply = addr_from if len(addr_from) > 0 else None
	send(config.feedback(), '[KSI-WEB] Zpetna vazba', '<p>'+text.decode('utf-8')+'</p>', True, config.mail_sender(), addr_reply)
