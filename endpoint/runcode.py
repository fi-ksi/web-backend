# -*- coding: utf-8 -*-

import falcon
import json
from datetime import datetime

from db import session
from sqlalchemy.exc import SQLAlchemyError
import model
import util
import traceback

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

            task_status = util.task.status(session.query(model.Task).get(module.task), user)

            if task_status == util.TaskStatus.LOCKED:
                resp.status = falcon.HTTP_400
                return

            execution = model.CodeExecution(
                module=module.id,
                user=user.id,
                code=data,
                time=datetime.utcnow(),
                report="",
            )

            reporter = util.programming.Reporter()
            try:
                result = util.programming.run(module, user.id, data, reporter)
                req.context['result'] = result
            except Exception as e:
                reporter += traceback.format_exc()
                req.context['result'] = { 'output': 'Kód se nepodařilo '
                    'spustit, kontaktujte organizátora.' }
                print(traceback.format_exc())

            execution.report = reporter.report
            session.add(execution)
            session.commit()

        except SQLAlchemyError:
            session.rollback()
            raise

        finally:
            session.close()

