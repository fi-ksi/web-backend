import smtplib
from email.mime.text import MIMEText
from email import Charset
import sys

from db import session
import random
import model
from util import config

def send(to, subject, text, easter_egg=False, addr_from=config.mail_sender(), addr_reply=None, return_path=config.get('return_path'), bcc=[]):
	Charset.add_charset('utf-8', Charset.QP, Charset.QP, 'utf-8')
	if easter_egg:
		rand = random.randrange(0, session.query(model.MailEasterEgg).count())
		egg = session.query(model.MailEasterEgg).all()[rand]
		text = u"<html>" + text + u"<hr/><p>PS: "  + egg.body + u"</p></html>"
	else:
		text = u"<html>" + text + u"</html>"

	msg = MIMEText(text, 'html', 'utf-8')

	msg['Subject'] = subject
	msg['From'] = addr_from
	msg['To'] = (','.join(to)) if isinstance(to, (list)) else to
	msg['Return-Path'] = return_path
	if addr_reply:
		msg['Reply-To'] = addr_reply

	try:
		s = smtplib.SMTP('relay.muni.cz')
		send_to = (to if isinstance(to, (list)) else [ to ]) + (bcc if isinstance(bcc, (list)) else [ bcc ])
		s.sendmail(addr_from, send_to, msg.as_string())
		s.quit()
	except:
		e = sys.exc_info()[0]
		print str(e)

def send_feedback(text, addr_from):
	addr_reply = addr_from if len(addr_from) > 0 else None
	send(config.feedback(), '[KSI-WEB] Zpetna vazba', '<p>'+text.decode('utf-8')+'</p>', True, config.mail_sender(), addr_reply)
