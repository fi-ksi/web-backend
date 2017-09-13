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

            try:
                execution = model.CodeExecution(
                    module=module.id,
                    user=user.id,
                    code=data,
                    time=datetime.utcnow(),
                    report="",
                )

                (user, report) = util.programming.run(module, user.id, data)
                req.context['result'] = user

                execution.report = report
                session.add(execution)
                session.commit()
            except:
                session.rollback()
                req.context['result'] = {
                    'output': 'Výjimka při operaci run, kontaktujte organizátora.',
                }
                raise

        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()

