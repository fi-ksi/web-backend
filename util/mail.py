import smtplib
from email.mime.text import MIMEText

FROM = 'ksi@fi.muni.cz'

def send(to, subject, text):
	#fp = open(textfile, 'rb')
	#msg = MIMEText(fp.read())
	#fp.close()

	msg = MIMEText(text)

	msg['Subject'] = subject
	msg['From'] = FROM
	msg['To'] = to

	s = smtplib.SMTP('relay.muni.cz')
	s.sendmail(FROM, [ to ], msg.as_string())
	s.quit()
