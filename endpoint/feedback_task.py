import json
from typing import Any, Dict, List, Tuple, Optional
import falcon
from sqlalchemy.exc import SQLAlchemyError
import datetime

from db import session
import model
from model.task import Task
import util
from util.feedback import (
    EForbiddenType,
    EUnmatchingDataType,
    EMissingAnswer,
    EOutOfRange,
)


class FeedbackTask(object):

    def on_get(self, req, resp, id):
        try:
            user = req.context['user']

            if not user.is_logged_in():
                resp.status = falcon.HTTP_400
                return

            feedback = session.query(model.Feedback).get((user.get_id(), id))

            if feedback is None:
                if session.query(model.Task).get(id) is None:
                    req.context['result'] = {
                        'errors': [{
                            'status': '404',
                            'title': 'Not found',
                            'detail': 'Úloha s tímto ID neexistuje.'
                        }]
                    }
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

            feedback = session.query(model.Feedback).get((user.get_id(), id))
            if feedback is None:
                feedback = model.Feedback(
                    user=user.get_id(),
                    task=id,
                    content='{}',
                )
                session.add(feedback)

            feedback.lastUpdated = datetime.datetime.utcnow()
            feedback.content = json.dumps(
                util.feedback.parse_feedback(data['categories']),
                indent=2,
                ensure_ascii=False,
            )

            session.commit()

        except (EForbiddenType, EUnmatchingDataType, EMissingAnswer,
                EOutOfRange) as e:
            req.context['result'] = {
                'errors': [{
                    'status': '400',
                    'title': 'Bad Request',
                    'detail': str(e)
                }]
            }
            resp.status = falcon.HTTP_400
            return
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

            feedback = session.query(model.Feedback).get((user.get_id(), id))
            if feedback is None:
                req.context['result'] = {
                    'errors': [{
                        'status': '404',
                        'title': 'Not found',
                        'detail': 'Feedback s tímto ID neexistuje.'
                    }]
                }
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

            task_id = int(data["taskId"])
            task = session.query(model.Task).get(task_id)
            if task is None:
                req.context['result'] = {
                    'errors': [{
                        'status': '404',
                        'title': 'Not found',
                        'detail': 'Úloha s tímto ID neexistuje.'
                    }]
                }
                resp.status = falcon.HTTP_404
                return

            content = json.dumps(
                util.feedback.parse_feedback(data["categories"]),
                indent=2,
                ensure_ascii=False,
            )

            user_id = user.get_id()
            feedback = model.Feedback(
                user=user_id,
                task=task_id,
                content=content,
                lastUpdated=datetime.datetime.utcnow(),
            )

            session.add(feedback)
            session.commit()

            req.context['result'] = {
                'feedback': util.feedback.to_json(feedback)
            }

            try:
                self._send_feedback_email_to_orgs(
                    task_id=task_id,
                    user_id=user_id,
                    feedback_content=data["categories"],
                )
            except BaseException:
                pass

        except (EForbiddenType, EUnmatchingDataType, EMissingAnswer,
                EOutOfRange) as e:
            req.context['result'] = {
                'errors': [{
                    'status': '400',
                    'title': 'Bad Request',
                    'detail': str(e)
                }]
            }
            resp.status = falcon.HTTP_400
            return
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()

    def _send_feedback_email_to_orgs(
        self, task_id: int, user_id: int, feedback_content: List[Dict[str, Any]]
    ):
        task = session.query(model.Task).get(task_id)
        body = self._get_feedback_email_body(task, user_id, feedback_content)
        if body is None:
            return

        author_email, recipients_copy = self._get_feedback_email_recipients(task)

        util.mail.send(
            to=author_email,
            subject=f"[KSI-WEB] Nový feedback k úloze {task.title}",
            text=body,
            cc=recipients_copy,
        )

    def _get_feedback_email_recipients(self, task: Task) -> Tuple[str, List[str]]:
        author_email = (
            session.query(model.User.email)
            .filter(model.User.id == task.author)
            .scalar()
        )
        wave_garant_email = (
            session.query(model.User.email)
            .join(model.Wave, model.Wave.garant == model.User.id)
            .join(model.Task, model.Task.wave == model.Wave.id)
            .filter(model.Task.id == task.id)
            .scalar()
        )
        recipients_copy = []
        if wave_garant_email != author_email:
            recipients_copy.append(wave_garant_email)

        if task.co_author is not None:
            co_author_email = (
                session.query(model.User.email)
                .filter(model.User.id == task.co_author)
                .scalar()
            )
            recipients_copy.append(co_author_email)
        return author_email, recipients_copy

    def _get_feedback_email_body(
        self, task: Task, user_id: int, feedback_content: List[Dict[str, Any]]
    ) -> Optional[str]:
        has_text_answer = any([self._get_answer_string(x)[1] for x in feedback_content])
        if not has_text_answer:
            return None

        user = session.query(model.User).get(user_id)

        feedback_text = "\n".join(
            [
                f"<p><i>\"{category['text']}\"</i>:</p><p>{self._get_answer_string(category)[0]}</p>"
                for category in feedback_content
            ]
        )
        ksi_web_url = util.config.ksi_web()
        return (
            f'<p>Ahoj,<br/>k tvé úloze <a href="{ksi_web_url}/ulohy/{task.id}" >'
            f"{task.title}</a> byl přidán nový feedback od "
            f"<b>{user.first_name} {user.last_name}:</b></p>"
            f"{feedback_text}"
            f"{util.config.mail_sign()}"
        )

    def _get_answer_string(self, rating_category: Dict[str, Any]) -> Tuple[str, bool]:
        answer = rating_category["answer"]
        contains_text_answer = False

        if rating_category["ftype"] in ["stars", "line"]:
            answer = "★" * answer + "☆" * (5 - answer)
        else:
            if str(answer).strip():
                contains_text_answer = True

        return answer, contains_text_answer
