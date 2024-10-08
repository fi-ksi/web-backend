import falcon
from sqlalchemy import func, or_, and_
from sqlalchemy.orm import aliased
from sqlalchemy.exc import SQLAlchemyError

from db import session
import model
import util


class CorrectionsEmail(object):

    def _send_single_email(self, task, participant, notify, points, post,
                           commenter, solution_comment):
        body = ("<p>Ahoj,<br>opravili jsme tvé řešení úlohy " +
                task.title + ".</p>")

        if participant.sex == 'female':
            body += ("<a>Získala jsi <strong>%.1f bodů</strong>."
                     "</p>" % points)
        else:
            body += ("<a>Získal jsi <strong>%.1f bodů</strong>."
                     "</p>" % points)

        if post:
            body += ("<p><a href=\"%s\"><i>%s</i></a> komentuje "
                     "tvé řešení:</p> %s") % (
                util.config.ksi_web() + "/profil/" +
                str(commenter.id),
                commenter.first_name + " " + commenter.last_name,
                post.body
            )
        else:
            body += ("<p>K tvému řešení nebyl přidán žádný komentář.</p>")

        if task.eval_comment:
            body += "<p>Společný komentář ke všem opravením:</p> %s" % (
                task.eval_comment
            )

        body += ("<p>Můžeš si prohlédnout <a href=\"%s\">výsledkovku</a>, ") % (
            util.config.ksi_web() + "#vysledky"
        )

        if solution_comment:
            body += ("podívat se na <a href=\"%s\">"
                     "vzorové řešení úlohy</a>, nebo <a href=\"%s\">"
                     "odpovědět na komentář opravujícího</a>.</p>") % (
                util.config.ksi_web() + "/ulohy/" +
                str(task.id) + "/reseni",
                util.config.ksi_web() + "/ulohy/" +
                str(task.id) + "#hodnoceni"
            )
        else:
            body += ("nebo se podívat na <a href=\"%s\">"
                     "vzorové řešení úlohy</a>.</p>") % (
                util.config.ksi_web() + "/ulohy/" +
                str(task.id) + "#reseni"
            )

        body += util.config.mail_sign()

        unsubscribe = util.mail.Unsubscribe(
            util.mail.EMailType.EVAL,
            notify,
            participant.id,
            commit=False, # we will commit new entries only once
            backend_url=util.config.backend_url(),
            ksi_web=util.config.ksi_web(),
        )

        util.mail.send(
            participant.email,
            f"{util.config.mail_subject_prefix()} Úloha %s opravena" % task.title,
            body,
            unsubscribe=unsubscribe,
            plaintext='' # No plaintext (pandoc is too slow for the bulk)
        )

    def on_put(self, req, resp, id):
        """
        1) Odeslani informacniho emailu resitelum, ve kterem se pise
            komentar opravujiciho a kolik ziskal resitel bodu.
        2) Odeslani informacniho emailu do ksi konference.
        ID je id ulohy

        """
        user = req.context['user']
        user_obj = user.user

        if (not user.is_logged_in()) or (not user.is_org()):
            req.context['result'] = {
                'errors': [{
                    'status': '403',
                    'title': 'Forbidden',
                    'detail': ('Informační e-mail může odeslat pouze '
                            'organizátor.')
                }]
            }
            resp.status = falcon.HTTP_400
            return

        try:
            task = session.query(model.Task).get(id)
            if not task.evaluation_public:
                req.context['result'] = {
                    'errors': [{
                        'status': '400',
                        'title': 'Bad Request',
                        'detail': 'Úloha nemá zveřejněné opravení.'
                    }]
                }
                resp.status = falcon.HTTP_400

            points_per_module = session.query(
                model.User.id.label('user'),
                model.Evaluation.module.label('module'),
                func.max(model.Evaluation.points).label('points'),
            ).\
                join(model.Evaluation, model.Evaluation.user == model.User.id).\
                join(model.Module, model.Evaluation.module == model.Module.id).\
                filter(model.Module.task == id).\
                group_by(model.User.id, model.Evaluation.module).subquery()

            participant = aliased(model.User)
            commenter = aliased(model.User)
            tos = session.query(
                participant,
                model.UserNotify,
                func.sum(points_per_module.c.points).label('points'),
                model.Post,
                commenter,
                model.SolutionComment
            ).\
                outerjoin(model.UserNotify, participant.id == model.UserNotify.user).\
                filter(or_(model.UserNotify.notify_eval, model.UserNotify.user == None)).\
                join(points_per_module,
                     points_per_module.c.user == participant.id).\
                outerjoin(model.SolutionComment,
                          and_(model.SolutionComment.user == participant.id,
                               model.SolutionComment.task == id)).\
                outerjoin(model.Post,
                          model.Post.thread == model.SolutionComment.thread).\
                outerjoin(commenter, commenter.id == model.Post.author).\
                group_by(participant).\
                all()

            errors = []
            for to in tos:
                try:
                    self._send_single_email(task, *to)
                except Exception as e:
                    errors.append(str(e))


            session.commit()

            # Odeslani informacniho emailu do konference
            try:
                body = "<p>Úloha <a href=\"%s\">%s</a> je opravena. \
                    %s právě odeslal" \
                    % (util.config.ksi_web() + "/ulohy/" + str(task.id),
                       task.title,
                       user_obj.first_name + " " + user_obj.last_name)

                if user_obj.sex == "female":
                    body += "a"

                body += " informační e-mail %s řešitelům.</p>" % len(tos)

                if task.eval_comment:
                    body += "<p>Společný komentář ke všem opravením:</p> %s" % (
                        task.eval_comment
                    )

                util.mail.send(
                    util.config.ksi_conf(),
                    f"{util.config.mail_subject_prefix()} Úloha %s opravena" % task.title,
                    body
                )
            except Exception as e:
                errors.append(str(e))

            req.context['result'] = {'count': len(tos)}
            if len(errors) > 0:
                req.context['result']['errors'] = errors
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()
