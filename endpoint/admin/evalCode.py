import falcon
import os
from sqlalchemy.exc import SQLAlchemyError

from db import session
import model


class EvalCode(object):

    def _file_or_error(self, fn):
        if not os.path.isfile(fn):
            return "Soubor %s neexistuje." % (fn)

        with open(fn, "r") as f:
            return f.read()

    def on_get(self, req, resp, id):
        try:
            user = req.context['user']

            if (not user.is_logged_in()) or (not user.is_org()):
                resp.status = falcon.HTTP_400
                return

            code = session.query(model.SubmittedCode).\
                filter(model.SubmittedCode.evaluation == id).first()

            if not code:
                req.context['result'] = {
                    'errors': [{'id': 5, 'title': "Code not found in db"}]
                }
                return

            evaluation = session.query(model.Evaluation).get(code.evaluation)
            if not evaluation:
                req.context['result'] = {
                    'errors': [
                        {'id': 5, 'title': "Evaluation not found in db"}
                    ]
                }
                return

            eval_dir = os.path.join(
                'data',
                'exec',
                'module_' + str(evaluation.module),
                'user_' + str(evaluation.user))

            CODE_PATH = os.path.join(eval_dir, 'box', 'run')
            STDOUT_PATH = os.path.join(eval_dir, 'stdout')
            STDERR_PATH = os.path.join(eval_dir, 'stderr')
            MERGE_STDOUT = os.path.join(eval_dir, 'merge.stdout')
            MERGE_STDERR = os.path.join(eval_dir, 'merge.stderr')

            req.context['result'] = {
                'evalCode': {
                    'id': evaluation.id,
                    'code': code.code,
                    'merged': self._file_or_error(CODE_PATH),
                    'stdout': self._file_or_error(STDOUT_PATH),
                    'stderr': self._file_or_error(STDERR_PATH),
                    'merge_stdout': self._file_or_error(MERGE_STDOUT),
                    'check_stdout': self._file_or_error(MERGE_STDERR),
                }
            }
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()
