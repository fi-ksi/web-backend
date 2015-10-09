import smtplib
from email.mime.text import MIMEText

KSI = 'ksi@fi.muni.cz'

def send(to, subject, text, addr_from=KSI):
	#fp = open(textfile, 'rb')
	#msg = MIMEText(fp.read())
	#fp.close()

	msg = MIMEText(text)

	msg['Subject'] = subject
	msg['From'] = addr_from
	msg['To'] = to

	s = smtplib.SMTP('relay.muni.cz')
	s.sendmail(addr_from, [ to ], msg.as_string())
	s.quit()
