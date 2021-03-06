import falcon
import json
from sqlalchemy.exc import SQLAlchemyError

from db import session
import model
import util


class AchievementGrant(object):

    def on_post(self, req, resp):
        """
        Prideleni achievementu

        Format dat:
        {
            "users": [ id ],
            "task": (null|id),
            "achievement": id
        }

        """
        try:
            user = req.context['user']
            data = json.loads(req.stream.read().decode('utf-8'))

            if (not user.is_logged_in()) or (not user.is_org()):
                resp.status = falcon.HTTP_400
                return

            errors = []
            req.context['result'] = {
                'errors': [{
                    'status': '401',
                    'title': 'Unauthorized',
                    'detail': 'Přístup odepřen.'
                }]
            }

            for u in data['users']:
                if not data['task']:
                    data['task'] = None
                else:
                    evl = session.query(model.Evaluation).\
                        filter(model.Evaluation.user == u).\
                        join(model.Module,
                             model.Module.id == model.Evaluation.module).\
                        filter(model.Module.task == data['task']).\
                        first()

                    if not evl:
                        errors.append({
                            'title': ("Uživatel " + str(u) +
                                      " neodevzdal vybranou úlohu\n")
                        })
                        continue

                if session.query(model.UserAchievement).\
                        get((u, data['achievement'])):
                    errors.append({
                        'title': ("Uživateli " + str(u) +
                                  " je již trofej přidělena\n")
                    })
                else:
                    ua = model.UserAchievement(
                        user_id=u,
                        achievement_id=data['achievement'],
                        task_id=data['task']
                    )
                    session.add(ua)

            session.commit()
            if len(errors) > 0:
                req.context['result'] = {'errors': errors}
            else:
                req.context['result'] = {}

        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()
