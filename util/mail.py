from email.mime.text import MIMEText
from email import charset as Charset
import sys
import copy
import threading
import random
import model
import smtplib
import queue

from db import session
from util import config

# Emaily jsou odesilane v parelelnim vlakne.

queueLock = threading.Lock()    # Zamek fronty emailQueue
emailQueue = queue.Queue()      # Fronta emailu k odeslani
emailThread = None              # Vlakno pro odesilani emailu


class emailData():
    """Jeden zaznam fronty emailu"""

    def __init__(self, frm, to, msg):
        self.frm = frm
        self.to = to
        self.msg = msg


class sendThread(threading.Thread):
    """Vlakno odesilajici postupne emaily.
    Vlakno bere emaily z fronty emailQueue, jakmile je fronta prazdna, vlakno
    konci.
    """

    def run(self):
        queueLock.acquire()
        try:
            while not emailQueue.empty():
                data = emailQueue.get()
                queueLock.release()

                s = smtplib.SMTP('relay.fi.muni.cz')
                s.sendmail(data.frm, data.to, data.msg)

                queueLock.acquire()
        finally:
            if s:
                s.quit()
            queueLock.release()


def easteregg():
    rand = random.randrange(0, session.query(model.MailEasterEgg).count())
    egg = session.query(model.MailEasterEgg).all()[rand]
    return "<hr><p>PS: " + egg.body + "</p>"


def send(to, subject, text, params={}, bcc=[], cc=[]):
    """Odeslani emailu."""

    global emailThread

    Charset.add_charset('utf-8', Charset.QP, Charset.QP, 'utf-8')
    text = "<html>" + text + "</html>"

    msg = MIMEText(text, 'html', 'utf-8')

    msg['Subject'] = subject
    msg['From'] = config.mail_sender()
    if 'Sender' not in msg:
        msg['Sender'] = config.get('return_path')
    msg['To'] = (','.join(to)) if isinstance(to, (list)) else to
    if len(cc) > 0:
        msg['Cc'] = (','.join(cc)) if isinstance(cc, (list)) else cc

    for key in list(params.keys()):
        msg[key] = params[key]

    send_to = set((to if isinstance(to, (list)) else [to]) +
                  (cc if isinstance(cc, (list)) else [cc]) +
                  (bcc if isinstance(bcc, (list)) else [bcc]))

    # Vlozime email do fronty
    queueLock.acquire()
    emailQueue.put(emailData(msg['Sender'], send_to, msg.as_string()))
    if emailThread and emailThread.isAlive():
        queueLock.release()
    else:
        queueLock.release()
        emailThread = sendThread()
        emailThread.start()


def send_multiple(to, subject, text, params={}, bcc=[]):
    """Odeslani hromadnych emailu"""

    bcc_params = copy.deepcopy(params)
    bcc_params['To'] = 'ksi-resitele@fi.muni.cz'
    bcc.append(config.ksi_conf())
    for b in bcc:
        bcc_params['Cc'] = b
        send([], subject, text, bcc_params, b)

    for recipient in to:
        send(recipient, subject, text, params)


def send_feedback(text, addr_from):
    addr_reply = addr_from if len(addr_from) > 0 else None
    params = {'Reply-To': addr_reply}
    send(config.feedback(), '[KSI-WEB] Zpetna vazba', '<p>' +
         text.decode('utf-8') + '</p>' + easteregg(), params)
