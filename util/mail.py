import smtplib
from email.mime.text import MIMEText
from email import Charset
import sys

from db import session
import random
import model
from util import config

def send(to, subject, text, easter_egg=False, addr_from=config.KSI_MAIL, addr_reply=None):
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
	msg['To'] = ','.join(to)
	msg['Content-Type'] = 'text/html'
	if addr_reply is not None:
		msg['Reply-To'] = addr_reply

	try:
		s = smtplib.SMTP('relay.muni.cz')
		s.sendmail(addr_from, to if isinstance(to, (list)) else [ to ], msg.as_string())
		s.quit()
	except:
		e = sys.exc_info()[0]
		print str(e)

def send_feedback(text, addr_from):
	addr_reply = addr_from if len(addr_from) > 0 else None
	send(config.FEEDBACK, '[KSI-WEB] Zpetna vazba', '<p>'+text.decode('utf-8')+'</p>', True, config.KSI_MAIL, addr_reply)
