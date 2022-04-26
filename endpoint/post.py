import json
import falcon
import sys
from sqlalchemy import text, distinct
from sqlalchemy.exc import SQLAlchemyError
import traceback

from db import session
import model
import util
from .thread import Thread
from util import config

MAX_POST_LEN = 8000


class Post(object):

    # Uprava prispevku
    def on_put(self, req, resp, id):
        try:
            user = req.context['user']

            if (not user.is_logged_in()) or (not user.is_org()):
                # Toto tady musi byt -- jinak nefunguje frontend.
                self.on_get(req, resp, id)
                return

            data = json.loads(req.stream.read().decode('utf-8'))['post']

            if len(data['body']) > MAX_POST_LEN:
                resp.status = falcon.HTTP_413
                req.context['result'] = {
                    'errors': [{
                        'status': '413',
                        'title': 'Payload too large',
                        'detail': ('Tělo příspěvku může mít maximálně ' +
                                   str(MAX_POST_LEN) + ' znaků.')
                    }]
                }
                return

            post = session.query(model.Post).get(id)
            if post is None:
                resp.status = falcon.HTTP_404
                return

            post.author = data['author']
            post.body = data['body']

            session.commit()
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()

        self.on_get(req, resp, id)

    def on_get(self, req, resp, id):
        try:
            user = req.context['user']
            user_id = req.context['user'].get_id()\
                if req.context['user'].is_logged_in() else None

            post = session.query(model.Post).get(id)

            if post is None:
                resp.status = falcon.HTTP_404
                return

            thread = session.query(model.Thread).get(post.thread)

            if thread is None:
                resp.status = falcon.HTTP_404
                return

            # Kontrola pristupu k prispevkum:
            # a) K prispevkum v eval vlakne mohou pristoupit jen orgove a
            #    jeden resitel
            # b) K ostatnim neverejnym prispevkum mohou pristoupit jen orgove.
            if (not thread.public and
                ((not user.is_logged_in()) or
                 (not user.is_org() and
                  not util.thread.is_eval_thread(user.id, thread.id)))):
                resp.status = falcon.HTTP_400
                return

            req.context['result'] = {'post': util.post.to_json(post, user_id)}
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()

    def on_delete(self, req, resp, id):
        try:
            user = req.context['user']

            if (not user.is_logged_in()) or (not user.is_org()):
                resp.status = falcon.HTTP_400
                return

            post = session.query(model.Post).get(id)
            if post is None:
                resp.status = falcon.HTTP_404
                return

            session.delete(post)
            session.commit()
            req.context['result'] = {}
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()


class Posts(object):

    def on_post(self, req, resp):
        try:
            if not req.context['user'].is_logged_in():
                resp.status = falcon.HTTP_400
                return

            user = req.context['user']
            data = json.loads(req.stream.read().decode('utf-8'))['post']

            if len(data['body']) > MAX_POST_LEN:
                resp.status = falcon.HTTP_413
                req.context['result'] = {
                    'errors': [{
                        'status': '413',
                        'title': 'Payload too large',
                        'detail': ('Tělo příspěvku může mít maximálně ' +
                                   str(MAX_POST_LEN) + ' znaků.')
                    }]
                }
                return

            thread_id = data['thread']
            thread = session.query(model.Thread).get(thread_id)

            if thread is None:
                resp.status = falcon.HTTP_400
                return

            if req.context['year_obj'].sealed:
                resp.status = falcon.HTTP_403
                req.context['result'] = {
                    'errors': [{
                        'status': '403',
                        'title': 'Forbidden',
                        'detail': 'Ročník zapečetěn.'
                    }]
                }
                return

            task_thread = session.query(model.Task).\
                filter(model.Task.thread == thread_id).\
                first()
            solution_thread = session.query(model.SolutionComment).\
                filter(model.SolutionComment.thread == thread_id,
                       model.SolutionComment.user == user.id).\
                first()

            if task_thread:
                prog_modules = session.query(model.Module).\
                    filter(model.Module.task == task_thread.id,
                           model.Module.type == model.ModuleType.PROGRAMMING).\
                    all()

            # Podminky pristupu:
            #  1) Do vlakna ulohy neni mozne pristoupit, pokud je uloha pro
            #     uzivatele uzavrena.
            #  2) K vlaknu komentare nemohou pristoupit dalsi resitele.
            #  3) Do obecnych neverejnych vlaken muhou pristupovat orgove --
            #     tato situace nastava pri POSTovani prnviho prispevku
            #     k opravovani, protoze vlakno opravovani jeste neni sprazeno
            #     s evaluation.
            if (task_thread and util.task.status(task_thread, user) == util.TaskStatus.LOCKED) or \
                (solution_thread and (solution_thread.user != user.id and not user.is_org())) or \
                    (not thread.public and not solution_thread and not user.is_org()):
                resp.status = falcon.HTTP_400
                return

            user_class = session.query(model.User).get(user.id)

            # Kontrola existence rodicovskeho vlakna
            parent = session.query(model.Post).\
                filter(model.Post.id == data['parent'],
                       model.Post.thread == thread_id).\
                first()
            if data['parent'] and not parent:
                resp.status = falcon.HTTP_400
                return

            # Aktualizace navstivenosti vlakna
            visit = util.thread.get_visit(user.id, thread_id)
            if visit:
                visit.last_last_visit = visit.last_visit
                visit.last_visit = text(
                    'CURRENT_TIMESTAMP + INTERVAL 1 SECOND')
            else:
                time = text('CURRENT_TIMESTAMP + INTERVAL 1 SECOND')
                visit = model.ThreadVisit(thread=thread_id, user=user.id,
                                          last_visit=time,
                                          last_last_visit=time)
                session.add(visit)
            session.commit()

            # Tady si pamatujeme, komu jsme email jiz odeslali
            sent_emails = set()

            # ------------------------------------------
            # Odesilani emailu orgum
            if user.role == 'participant' or user.role == 'participant_hidden':

                if task_thread:
                    # Vlakno k uloze -> posilame email autoru ulohy,
                    # spoluautoru ulohy a garantovi vlny.
                    task_author_email = session.query(model.User.email).\
                        filter(model.User.id == task_thread.author).\
                        scalar()
                    recipients = [task_author_email]
                    wave_garant_email = session.query(model.User.email).\
                        join(model.Wave, model.Wave.garant == model.User.id).\
                        join(model.Task, model.Task.wave == model.Wave.id).\
                        filter(model.Task.id == task_thread.id).scalar()
                    sent_emails.add(task_author_email)
                    sent_emails.add(wave_garant_email)
                    if task_thread.co_author:
                        task_co_author_email = session.query(model.User.email).\
                            filter(model.User.id == task_thread.co_author).\
                            scalar()
                        sent_emails.add(task_co_author_email)
                        recipients.append(task_co_author_email)
                    try:
                        body = (
                            '<p>Ahoj,<br/>k tvé úloze <a href="' +
                            config.ksi_web() + '/ulohy/' + str(task_thread.id) +
                            '">' + task_thread.title + '</a> na <a href="' +
                            config.ksi_web() + '/">' + config.ksi_web() +
                            '</a> byl přidán nový komentář:</p><p><i>' +
                            user_class.first_name + ' ' + user_class.last_name +
                            ':</i></p>' + data['body'] + '<p><a href="' +
                            config.ksi_web() + '/ulohy/' + str(task_thread.id) +
                            '/diskuse">Přejít do diskuze.</a> ' + '<a href="' +
                            config.ksi_web() + '/admin/opravovani?participant_=' +
                            str(user_class.id) + '&task_=' + str(task_thread.id) +
                            '">Přejít na opravení.</a>'
                        )

                        if len(prog_modules) > 0:
                            body += (' <a href="' + config.ksi_web() +
                                     '/admin/execs?user=' + str(user_class.id))
                            if len(prog_modules) == 1:
                                body += '&module=' + str(prog_modules[0].id)

                            body += '">Přejít na spuštění.</a></p>'

                        body += '</p>'
                        body += config.mail_sign()

                        util.mail.send(
                            recipients,
                            '[Naskoc na FI] Nový příspěvek k úloze ' + task_thread.title,
                            body,
                            cc=wave_garant_email
                        )
                    except BaseException:
                        exc_type, exc_value, exc_traceback = sys.exc_info()
                        traceback.print_exception(
                            exc_type, exc_value, exc_traceback,
                            file=sys.stderr
                        )

                elif solution_thread:
                    # Vlakno k oprave -> posilame email autoru opravy
                    correctors = [
                        r for r, in
                        session.query(distinct(model.User.email)).
                        join(model.Evaluation,
                             model.Evaluation.evaluator == model.User.id).
                        join(model.Module,
                             model.Evaluation.module == model.Module.id).
                        join(model.Task, model.Task.id == model.Module.task).
                        filter(model.Task.id == solution_thread.task).all()
                    ]

                    for corr_email in correctors:
                        sent_emails.add(corr_email)

                    if correctors:
                        task = session.query(model.Task).\
                            get(solution_thread.task)
                        try:
                            util.mail.send(
                                correctors,
                                '[Naskoc na FI] Nový komentář k tvé korektuře úlohy ' + task.title,
                                '<p>Ahoj,<br/>k tvé <a href="' +
                                config.ksi_web() + '/admin/opravovani?task_=' +
                                str(task.id) + '&participant_='+str(user_class.id) +
                                '">korektuře</a> úlohy <a href="' + config.ksi_web() +
                                '/ulohy/' + str(task.id) + '">' + task.title +
                                '</a> na <a href="' + config.ksi_web() + '/">' +
                                config.ksi_web() +
                                '</a> byl přidán nový komentář:<p><p><i>' +
                                user_class.first_name + ' ' +
                                user_class.last_name + ':</i></p><p>' +
                                data['body'] + config.mail_sign())
                        except BaseException:
                            exc_type, exc_value, exc_traceback = sys.exc_info()
                            traceback.print_exception(exc_type, exc_value,
                                                      exc_traceback,
                                                      file=sys.stderr)
                else:
                    # Obecna diskuze -> email na ksi@fi.muni.cz
                    try:
                        sent_emails.add(config.ksi_conf())
                        util.mail.send(
                            config.ksi_conf(),
                            '[Naskoc na FI] Nový příspěvek v obecné diskuzi',
                            '<p>Ahoj,<br/>do obecné diskuze na <a href="' +
                            config.ksi_web() + '/">' + config.ksi_web() +
                            '</a> byl přidán nový příspěvek:</p><p><i>' +
                            user_class.first_name + ' ' +
                            user_class.last_name + ':</i></p>' + data['body'] +
                            '<p><a href=' + config.ksi_web() + '/forum/' +
                            str(thread.id) + '>Přejít do diskuze.</a></p>' +
                            config.mail_sign()
                        )
                    except BaseException:
                        exc_type, exc_value, exc_traceback = sys.exc_info()
                        traceback.print_exception(exc_type, exc_value,
                                                  exc_traceback,
                                                  file=sys.stderr)

            # ------------------------------------------
            # Pridani prispevku
            post = model.Post(thread=thread_id, author=user.id,
                              body=data['body'], parent=data['parent'])
            session.add(post)
            session.commit()

            # ------------------------------------------
            # Odesilani emailu v reakci na muj prispevek:

            if parent:
                parent_user = session.query(model.User).get(parent.author)
                parent_notify = util.user_notify.get(parent.author)
                if (parent_user.email not in sent_emails and
                        parent_notify.notify_response):
                    try:
                        sent_emails.add(parent_user.email)

                        body = (
                            '<p>Ahoj,<br>do diskuze <a href="%s">%s</a> byl '
                            'přidán nový příspěvek.</p>' %
                            (util.config.ksi_web() + "/forum/" +
                             str(thread.id), thread.title)
                        )
                        body += util.post.to_html(parent, parent_user)
                        body += ("<div style='margin-left: 50px;'>%s</div>" %
                                 (util.post.to_html(post)))
                        body += util.config.mail_sign()

                        util.mail.send(
                            parent_user.email,
                            ('[Naskoc na FI] Nový příspěvek v diskuzi %s' %
                             (thread.title)),
                            body,
                            unsubscribe=util.mail.Unsubscribe(
                                email_type=util.mail.EMailType.RESPONSE,
                                user_id=parent_user.id,
                            ),
                        )
                    except BaseException:
                        exc_type, exc_value, exc_traceback = sys.exc_info()
                        traceback.print_exception(exc_type, exc_value,
                                                  exc_traceback,
                                                  file=sys.stderr)

            req.context['result'] = {'post': util.post.to_json(post, user.id)}
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()
