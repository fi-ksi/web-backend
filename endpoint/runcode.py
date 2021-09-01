import falcon
import json
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
import traceback

from db import session
import model
import util


class RunCode(object):

    def on_post(self, req, resp, id):
        try:
            user = req.context['user']
            if not user.is_logged_in():
                resp.status = falcon.HTTP_400
                return

            data = json.loads(req.stream.read().decode('utf-8'))['content']
            module = session.query(model.Module).get(id)

            if not module:
                resp.status = falcon.HTTP_400
                return

            task_status = util.task.status(session.query(model.Task).
                                           get(module.task), user)

            if task_status == util.TaskStatus.LOCKED:
                resp.status = falcon.HTTP_400
                return

            execution = model.CodeExecution(
                module=module.id,
                user=user.id,
                code=data,
                result='error',
                time=datetime.utcnow(),
                report="",
            )
            session.add(execution)
            session.commit()

            reporter = util.programming.Reporter()
            try:
                try:
                    result = util.programming.run(module, user.id, data,
                                                  execution.id, reporter)
                    execution.result = result['result']
                    req.context['result'] = result
                except (util.programming.ENoFreeBox,
                        util.programming.EIsolateError,
                        util.programming.EPostTriggerError,
                        util.programming.ECheckError,
                        util.programming.EMergeError) as e:
                    reporter += str(e)
                    raise
                except Exception as e:
                    reporter += traceback.format_exc()
                    raise

            except Exception as e:
                req.context['result'] = {
                    'message': ('Kód se nepodařilo '
                                'spustit, kontaktujte organizátora.'),
                    'result': 'error',
                }

            if user.is_org():
                req.context['result']['report'] = reporter.report

            # truncate too long reports (possibly from cycled programs)
            report_text = reporter.report
            report_text_safe_length = 640 * 1024  # ~640KiB, max is 16MiB for MEDIUMTEXT
            if len(report_text.encode('utf-8')) > report_text_safe_length:
                report_text = report_text[:report_text_safe_length] + f" [ZKRÁCENO Z {len(report_text)} ZNAKŮ]"

            execution.report = report_text
            session.commit()

        except SQLAlchemyError:
            session.rollback()
            raise

        finally:
            session.close()
