import smtplib
from email.mime.text import MIMEText
from email import Charset

from db import session
import random
import model

KSI = session.query(model.Config).get("mail_sender").value
FEEDBACK = [ 'me@apophis.cz' ]

def send(to, subject, text, easter_egg=False, addr_from=KSI):
	Charset.add_charset('utf-8', Charset.QP, Charset.QP, 'utf-8')
	if easter_egg:
		rand = random.randrange(0, session.query(model.MailEasterEgg).count()) 
		egg = session.query(model.MailEasterEgg).all()[rand]
		text = u"<html>" + text + "<hr/><p>PS: "  + egg.body + u"</p></html>"
	else:
		text = u"<html>" + text + u"</html>"

	msg = MIMEText(text, 'html', 'utf-8')

	msg['Subject'] = subject
	msg['From'] = addr_from
	msg['To'] = ','.join(to)
	msg['Content-Type'] = 'text/html'

	s = smtplib.SMTP('relay.muni.cz')
	s.sendmail(addr_from, to if isinstance(to, (list)) else [ to ], msg.as_string())
	s.quit()

def send_feedback(text, addr_from):
	addr_from = addr_from if len(addr_from) > 0 else KSI

	send(FEEDBACK, '[KSI-WEB] Zpetna vazba', text, addr_from)
