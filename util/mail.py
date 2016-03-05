# -*- coding: utf-8 -*-

from email.mime.text import MIMEText
from email import Charset
import sys, copy, threading, random, model, smtplib, Queue

from db import session
from util import config

# Emaily jsou odesilane v parelelnim vlakne.

queueLock = threading.Lock()	# Zamek fronty emailQueue
emailQueue = Queue.Queue()		# Fronta emailu k odeslani
emailThread = None				# Vlakno pro odesilani emailu

# Jeden zaznam fronty emailu
class emailData():
	def __init__(self, frm, to, msg):
		self.frm = frm
		self.to = to
		self.msg = msg

# Vlakno odesilajici postupne emaily.
# Vlakno bere emaily z fronty emailQueue, jakmile je fronta prazdna, vlakno konci.
class sendThread(threading.Thread):
	def run(self):
		queueLock.acquire()
		try:
			while not emailQueue.empty():
				data = emailQueue.get()
				queueLock.release()

				s = smtplib.SMTP('relay.muni.cz')
				s.sendmail(data.frm, data.to, data.msg)

				queueLock.acquire()
		finally:
			if s: s.quit()
			queueLock.release()

def easteregg():
	rand = random.randrange(0, session.query(model.MailEasterEgg).count())
	egg = session.query(model.MailEasterEgg).all()[rand]
	return u"<hr><p>PS: "  + egg.body + u"</p>"

# Odeslani emailu.
def send(to, subject, text, params={}, bcc=[]):
	global emailThread

	Charset.add_charset('utf-8', Charset.QP, Charset.QP, 'utf-8')
	text = u"<html>" + text + u"</html>"

	msg = MIMEText(text, 'html', 'utf-8')

	msg['Subject'] = subject
	msg['From'] = config.mail_sender()
	msg['Sender'] = 'ksi-admin@fi.muni.cz'
	msg['To'] = (','.join(to)) if isinstance(to, (list)) else to
	msg['Return-Path'] = config.get('return_path')
	msg['Errors-To'] = config.get('return_path')

	for key in params.keys(): msg[key] = params[key]

	send_to = (to if isinstance(to, (list)) else [ to ]) + (bcc if isinstance(bcc, (list)) else [ bcc ])

	# Vlozime email do fronty
	queueLock.acquire()
	emailQueue.put(emailData(msg['From'], send_to, msg.as_string()))
	if emailThread and emailThread.isAlive():
		queueLock.release()
	else:
		queueLock.release()
		emailThread = sendThread()
		emailThread.start()

# Odeslani hromadnych emailu
def send_multiple(to, subject, text, params={}, bcc=[]):
	bcc_params = copy.deepcopy(params)
	bcc_params['To'] = 'undisclosed-recipients@fi.muni.cz'
	bcc.append(config.ksi_conf())
	for b in bcc:
		bcc_params['Cc'] = b
		send([], subject, text, bcc_params, b)

	for recipient in to:
		send(recipient, subject, text, params)

def send_feedback(text, addr_from):
	addr_reply = addr_from if len(addr_from) > 0 else None
	params = { 'Reply-To': addr_reply }
	send(config.feedback(), '[KSI-WEB] Zpetna vazba', '<p>'+text.decode('utf-8')+'</p>' + easteregg(), params)

