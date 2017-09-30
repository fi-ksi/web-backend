import falcon
from sqlalchemy.exc import SQLAlchemyError

from db import session
import model
import util


class Evaluation(object):

    def on_get(self, req, resp, id):
        """
        GET pozadavek na konkretni correction se spousti prevazne jako odpoved
        na POST.
        id je umele id, konstrukce viz util/correction.py
        Parametry: moduleX_version=Y (X a Y jsou cisla)

        """

        try:
            user = req.context['user']

            if (not user.is_logged_in()) or (not user.is_org()):
                resp.status = falcon.HTTP_400
                return

            evaluation = session.query(model.Evaluation).get(id)
            if evaluation is None:
                resp.status = falcon.HTTP_404
                return

            module = session.query(model.Module).get(evaluation.module)

            req.context['result'] = {
                'evaluation': util.correction.corr_eval_to_json(module,
                                                                evaluation)
            }
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()
