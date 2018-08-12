import json
import falcon
from sqlalchemy.exc import SQLAlchemyError
import datetime

from db import session
import model
import util

MAX_CATEGORIES = 16
MAX_ID_LEN = 32
MAX_TYPE_LEN = 32
MAX_QUESTION_LEN = 1024
MAX_ANSWER_LEN = 8192

class FeedbackTask(object):

    def on_get(self, req, resp, id):
        try:
            user = req.context['user']

            if not user.is_logged_in():
                resp.status = falcon.HTTP_400
                return

            feedback = session.query(model.Feedback).get((user, id))

            if feedback is None:
                if session.query(model.Task).get(id) is None:
                    resp.status = falcon.HTTP_404
                    return

                req.context['result'] = {
                    'feedback': util.feedback.empty_to_json(id, user.get_id())
                }
                return

            req.context['result'] = {
                'feedback': util.feedback.to_json(feedback)
            }

        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()

    def on_put(self, req, resp, id):
        """Update feedback."""
        try:
            user = req.context['user']

            if not user.is_logged_in():
                resp.status = falcon.HTTP_400
                return

            data = json.loads(req.stream.read().decode('utf-8'))['feedback']

            feedback = session.query(model.Feedback).get((user, id))
            if feedback is None:
                feedback = model.Feedback(
                    user=user,
                    task=id,
                    content='{}',
                )
                session.add(feedback)

            feedback.lastUpdated = datetime.datetime.utcnow()
            feedback.content = json.dumps(
                util.feedback.parse_feedback(data['feedback']['categories']),
                indent=2
            )

            session.commit()

        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()

        self.on_get(req, resp, id)

    def on_delete(self, req, resp, id):
        """Delete feedback"""
        try:
            user = req.context['user']

            if not user.is_logged_in():
                resp.status = falcon.HTTP_400
                return

            feedback = session.query(model.Feedback).get((user, id))
            if feedback is None:
                resp.status = falcon.HTTP_404
                return

            session.delete(feedback)
            session.commit()
            req.context['result'] = {}

        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()


class FeedbacksTask(object):

    def on_post(self, req, resp):
        """Create new feedback"""
        try:
            user = req.context['user']

            if not user.is_logged_in():
                resp.status = falcon.HTTP_400
                return

            data = json.loads(req.stream.read().decode('utf-8'))['feedback']

            if session.query(model.Task).get(int(data['taskId'])) is None:
                resp.status = falcon.HTTP_404
                return

            content = json.dumps(
                util.feedback.parse_feedback(data['categories']),
                indent=2
            )

            feedback = model.Feedback(
                user=user,
                task=int(data['taskId']),
                content=content,
                lastUpdated = datetime.datetime.utcnow(),
            )

            session.add(feedback)
            session.commit()

            req.context['result'] = {
                'feedback': util.feedback.to_json(feedback)
            }

        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()
