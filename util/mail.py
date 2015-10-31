import smtplib
from email.mime.text import MIMEText
from email import Charset

KSI = 'ksi-dev@fi.muni.cz'
FEEDBACK = [ 'me@apophis.cz' ]

def send(to, subject, text, addr_from=KSI):
	Charset.add_charset('utf-8', Charset.QP, Charset.QP, 'utf-8')
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
