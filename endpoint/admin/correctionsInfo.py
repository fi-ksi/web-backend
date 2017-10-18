import falcon
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from db import session
import model
import util


class CorrectionInfo(object):

    def on_get(self, req, resp, id):
        try:
            user = req.context['user']
            year = req.context['year']

            if (not user.is_logged_in()) or (not user.is_org()):
                resp.status = falcon.HTTP_400
                return

            task = session.query(model.Task).get(id)
            if not task:
                resp.status = falcon.HTTP_404
                return

            req.context['result'] = {
                'correctionsInfo': util.correctionInfo.task_to_json(task)
            }
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()


class CorrectionsInfo(object):

    def on_get(self, req, resp):
        """
        Specifikace GET pozadavku:
        Prazdny pozadavek vracici ulohy, vlny a uzivatele pro vyplneni filtru
        opravovatka.

        """

        try:
            user = req.context['user']
            year = req.context['year']

            if (not user.is_logged_in()) or (not user.is_org()):
                req.context['result'] = {
                    'errors': [{
                        'status': '401',
                        'title': 'Unauthorized',
                        'detail': ('Přístup k opravovátku mají pouze '
                                   'organizátoři.')
                    }]
                }
                resp.status = falcon.HTTP_400
                return

            tasks = session.query(model.Task).\
                join(model.Wave, model.Wave.id == model.Task.wave).\
                filter(model.Wave.year == year).all()

            waves = session.query(model.Wave).\
                filter(model.Wave.year == year).\
                join(model.Task, model.Task.wave == model.Wave.id).all()

            users = session.query(model.User)
            users = set(util.user.active_in_year(users, year).all())
            users |= set(session.query(model.User).
                         join(model.Task,
                         model.Task.author == model.User.id).all())

            solvers = session.query(model.Task.id, model.Evaluation.user).\
                join(model.Wave, model.Wave.id == model.Task.wave).\
                filter(model.Wave.year == year).\
                join(model.Module, model.Module.task == model.Task.id).\
                join(model.Evaluation,
                     model.Module.id == model.Evaluation.module).\
                group_by(model.Task, model.Evaluation.user).\
                all()

            evaluating = session.query(model.Task.id).\
                join(model.Module, model.Module.task == model.Task.id).\
                filter(model.Evaluation.evaluator != None).\
                join(model.Evaluation,
                     model.Evaluation.module == model.Module.id).\
                all()
            evaluating = [r for (r,) in evaluating]

            req.context['result'] = {
                'correctionsInfos': [
                    util.correctionInfo.task_to_json(
                        task,
                        list(map(
                            lambda t: t[1],
                            filter(lambda t: t[0] == task.id, solvers)
                        )),
                        task.id in evaluating
                    ) for task in tasks
                ],
                'waves': [
                    util.wave.to_json(wave) for wave in waves
                ],
                'users': [
                    util.correctionInfo.user_to_json(user) for user in users
                ]
            }

        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()
