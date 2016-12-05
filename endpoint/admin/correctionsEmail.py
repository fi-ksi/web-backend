# -*- coding: utf-8 -*-

import falcon
from sqlalchemy import func, or_
from sqlalchemy.orm import aliased
from sqlalchemy.exc import SQLAlchemyError
from db import session
import model, util

class CorrectionsEmail(object):

    """
        1) Odeslani informacniho emailu resitelum, ve kterem se pise
            komentar opravujiciho a kolik ziskal resitel bodu.
        2) Odeslani informacniho emailu do ksi konference.
        ID je id ulohy
    """
    def on_put(self, req, resp, id):
        user = req.context['user']
        user_obj = user.user

        if (not user.is_logged_in()) or (not user.is_org()):
            req.context['result'] = { 'errors': [ { 'status': '403', 'title': 'Forbidden', 'detail': u'Informační e-mail může odeslat pouze organizátor.' } ] }
            resp.status = falcon.HTTP_400
            return

        try:
            task = session.query(model.Task).get(id)
            if not task.evaluation_public:
                req.context['result'] = { 'errors': [ { 'status': '400', 'title': 'Bad Request', 'detail': u'Úloha nemá zveřejněné opravení.' } ] }
                resp.status = falcon.HTTP_400

            participant = aliased(model.User)
            evaluator = aliased(model.User)
            tos = session.query(participant, model.Profile, model.Evaluation, model.Post, evaluator).\
                join(model.Profile, participant.id == model.Profile.user_id).\
                filter(model.Profile.notify_eval).\
                join(model.Evaluation, model.Evaluation.user == participant.id).\
                join(model.Module, model.Module.id == model.Evaluation.module).\
                join(evaluator, evaluator.id == model.Evaluation.evaluator).\
                filter(model.Module.task == id).\
                outerjoin(model.SolutionComment, model.SolutionComment.user == participant.id).\
                filter(or_(model.SolutionComment.task == id, model.SolutionComment.thread == None)).\
                outerjoin(model.Post, model.Post.thread == model.SolutionComment.thread).\
                group_by(participant).all()

            author = session.query(model.User).get(task.author)
            errors = []

            for to in tos:
                try:

                    body = u"<p>Ahoj,<br>opravili jsme tvé řešení úlohy " + task.title + u".</p>"

                    if to[0].sex == 'female':
                        body += u"<a>Získala jsi <strong>%.1f bodů</strong>.</p>" % to.Evaluation.points
                    else:
                        body += u"<a>Získal jsi <strong>%.1f bodů</strong>.</p>" % to.Evaluation.points

                    if to.Post:
                        body += u"<p><a href=\"%s\"><i>%s</i></a> komentuje tvé řešení:</p> %s" % (util.config.ksi_web() + "/profil/" +str(to[4].id), to[4].first_name + " " + to[4].last_name, to.Post.body)
                    else:
                        body += u"<p>K tvému řešení nebyl přidán žádný komentář.</p>"

                    body += u"<p>Můžeš si prohlédnout <a href=\"%s\">výsledkovku</a>, podívat se na <a href=\"%s\">vzorové řešení úlohy</a>, nebo <a href=\"%s\">odpovědět na komentář opravujícího</a>.</p>" % (util.config.ksi_web()+"/vysledky", util.config.ksi_web()+"/ulohy/"+str(id)+"/reseni", util.config.ksi_web()+"/ulohy/"+str(id)+"/hodnoceni")
                    body += util.config.karlik_img()

                    body += u"<hr><p style='font-size: 70%%;'>Tuto zprávu dostáváš, protože máš v nastavení na <a href=\"%s\">KSI webu</a> aktivované zasílání notifikací. Pokud nechceš dostávat notifikace, změň si nastavení na webu.</p>" % (util.config.ksi_web())

                    util.mail.send(to[0].email, u"[KSI-WEB] Úloha %s opravena" % task.title, body)
                except Exception as e:
                    errors.append( str(e) )
                    #raise

            # Odeslani informacniho emailu do konference
            try:
                body = u"<p>Úloha <a href=\"%s\">%s</a> je opravena. \
                    %s právě odeslal" \
                    % (util.config.ksi_web()+"/ulohy/"+str(task.id), task.title, user_obj.first_name+" "+user_obj.last_name)
                if user_obj.sex == "female": body += "a"
                body +=  u" informační e-mail %s řešitelům.</p>" % len(tos)
                util.mail.send(util.config.ksi_conf(), u"[KSI-WEB] Úloha %s opravena" % task.title, body)
            except Exception as e:
                errors.append( str(e) )
                #raise


            req.context['result'] = { 'count': len(tos) }
            if len(errors) > 0: req.context['result']['errors'] = errors
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()

