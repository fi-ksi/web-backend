from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email import charset as Charset
import sys
import copy
import threading
import random
import model
import smtplib
import queue
from enum import Enum
from collections import namedtuple
import pypandoc

from db import session
from util import config
import util

# Emaily jsou odesilane v paralelnim vlakne.

queueLock = threading.Lock()    # Zamek fronty emailQueue
emailQueue = queue.Queue()      # Fronta emailu k odeslani
emailThread = None              # Vlakno pro odesilani emailu

class EMailType(Enum):
    EVAL = 0
    RESPONSE = 1
    KSI = 2
    EVENTS = 4

UNSUBSCRIBE_LINK = {
    EMailType.EVAL: 'eval',
    EMailType.RESPONSE: 'response',
    EMailType.KSI: 'ksi',
    EMailType.EVENTS: 'events',
}

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

                try:
                    s = smtplib.SMTP('relay.fi.muni.cz')
                    s.sendmail(data.frm, data.to, data.msg)
                except Exception as e:
                    print(str(e))

                queueLock.acquire()
        finally:
            if s:
                s.quit()
            if queueLock.locked():
                queueLock.release()


def easteregg():
    rand = random.randrange(0, session.query(model.MailEasterEgg).count())
    egg = session.query(model.MailEasterEgg).all()[rand]
    return "<hr><p>PS: " + egg.body + "</p>"


def _send(to, subject, text, params, bcc, cc, plaintext=None):
    """Odeslani emailu."""

    global emailThread

    Charset.add_charset('utf-8', Charset.QP, Charset.QP, 'utf-8')
    text = "<html>" + text + "</html>"

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = config.mail_sender()
    if 'Sender' not in params:
        msg['Sender'] = config.get('return_path')
    if 'Return-Path' not in params:
        msg['Return-Path'] = config.get('return_path')
    msg['To'] = (','.join(to)) if isinstance(to, (list)) else to
    if len(cc) > 0:
        msg['Cc'] = (','.join(cc)) if isinstance(cc, (list)) else cc

    for key in list(params.keys()):
        msg[key] = params[key]

    if plaintext is None:
        plaintext = pypandoc.convert(text, 'markdown', format='html')

    msg.attach(MIMEText(plaintext, 'plain', 'utf-8'))
    msg.attach(MIMEText(text, 'html', 'utf-8'))

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


def send(to, subject, text, unsubscribe=None, params=None, bcc=None, cc=None, plaintext=None):
    if params is None:
        params = {}
    if bcc is None:
        bcc = []
    if cc is None:
        cc = []

    if unsubscribe is not None:
        text += unsubscribe.text()
        plaintext += unsubscribe.plaintext()
        if hasattr(unsubscribe, 'link'):
            params['List-Unsubscribe-Post'] = 'List-Unsubscribe=One-Click'
            params['List-Unsubscribe'] = '<' + unsubscribe.link() + '>'

    _send(to, subject, text, params, bcc, cc, plaintext)


EMailRecipient = namedtuple('EMailRecipient', ['to', 'unsunscribe'])


def send_multiple(recipients, subject, text, params={}, bcc=[]):
    """Odeslani hromadnych emailu"""

    plaintext = pypandoc.convert(text, 'markdown', format='html')

    bcc_params = copy.deepcopy(params)
    bcc_params['To'] = 'ksi-resitele@fi.muni.cz'
    bcc.append(config.ksi_conf())
    for b in bcc:
        bcc_params['Cc'] = b
        send([], subject, text, FakeUnsubscribe(), bcc_params, b, plaintext=plaintext)

    for to, unsubscribe in recipients:
        send(to, subject, text, unsubscribe, params, plaintext=plaintext)


def send_feedback(text, addr_from):
    addr_reply = addr_from if len(addr_from) > 0 else None
    params = {'Reply-To': addr_reply}
    send(config.feedback(), '[KSI-WEB] Zpetna vazba', '<p>' +
         text.decode('utf-8') + '</p>' + easteregg(), params)


class Unsubscribe:
    def __init__(self, email_type, notify=None, user_id=None, commit=True,
                 backend_url=None, ksi_web=None):
        if notify is None:
            notify = session.query(model.UserNotify).get(user_id)
            if notify is None:
                notify = util.user_notify.normalize(notify, user_id)
                session.add(notify)
                if commit:
                    session.commit()

        self.email_type = email_type
        self.notify = notify
        self.user_id = user_id
        self.commit = commit
        self.backend_url = backend_url if backend_url is not None else util.config.backend_url()
        self.ksi_web = ksi_web if ksi_web is not None else util.config.ksi_web()

    def text(self):
        return (
            '<hr><p style="font-size: 70%%;">Pokud nechceš dostávat tyto notifikace, '
            'změň si nastavení na <a href="%s">KSI webu</a> nebo klikni na '
            '<a href="%s">odhlásit se</a>.</p>' % (
                self.ksi_web,
                self.link(),
            )
        )

    def plaintext(self):
        return (
            '\n\nPokud nechceš dostávat tyto notifikace,\n'
            'změň si nastavení na %s nebo klikni na přímý odkaz:\n%s' % (
                self.ksi_web,
                self.link(),
            )
        )

    def link(self):
        return (
            '%s/unsubscribe/%d?token=%s&type=%s' % (
                self.backend_url,
                self.notify.user,
                self.notify.auth_token,
                UNSUBSCRIBE_LINK[self.email_type],
            )
        )


class FakeUnsubscribe:
    def text(self):
        return (
            '<hr><p style="font-size: 70%;">Na tomto místě je přímý odkaz na '
            'odhlášení odběru, který vypadá takto:<br>Pokud nechceš dostávat tyto '
            'notifikace, změň si nastavení na <a href="">KSI webu</a> nebo '
            'klikni na <a href="">odhlásit se</a>.</p>'
        )

    def plaintext(self):
        return (
            '\n\nTady je plaintextová verze unsubscribe, ale tu snad nikdo nečte...'
        )
