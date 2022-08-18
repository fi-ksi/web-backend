import falcon
import json
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError

import util
from db import session
import model
from util.config import successful_participant_trophy_id


class Achievement(object):

    def on_get(self, req, resp, id):
        try:
            achievement = session.query(model.Achievement).get(id)
        except SQLAlchemyError:
            session.rollback()
            raise

        if achievement is None:
            req.context['result'] = {
                'errors': [{
                    'status': '404',
                    'title': 'Not found',
                    'detail': 'Trofej s tímto ID neexistuje.'
                }]
            }
            resp.status = falcon.HTTP_404
            return

        req.context['result'] = {
            'achievement': util.achievement.to_json(achievement)
        }

    def on_delete(self, req, resp, id):
        user = req.context['user']
        try:
            achievement = session.query(model.Achievement).get(id)
        except SQLAlchemyError:
            session.rollback()
            raise

        if (not user.is_logged_in()) or (not user.is_admin()):
            req.context['result'] = {
                'errors': [{
                    'status': '401',
                    'title': 'Unauthorized',
                    'detail': ('Smazání trofeje může provést pouze '
                               'administrátor.')
                }]
            }
            resp.status = falcon.HTTP_400
            return

        if not achievement:
            req.context['result'] = {
                'errors': [{
                    'status': '404',
                    'title': 'Not Found',
                    'detail': 'Trofej s tímto ID neexsituje.'
                }]
            }
            resp.status = falcon.HTTP_404
            return

        try:
            session.delete(achievement)
            session.commit()
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()

        req.context['result'] = {}

    # UPDATE trofeje
    def on_put(self, req, resp, id):
        user = req.context['user']

        # Upravovat trofeje mohou jen orgove
        if (not user.is_logged_in()) or (not user.is_org()):
            req.context['result'] = {
                'errors': [{
                    'status': '401',
                    'title': 'Unauthorized',
                    'detail': 'Úpravu trofeje může provést pouze organizátor.'
                }]
            }
            resp.status = falcon.HTTP_400
            return

        data = json.loads(req.stream.read().decode('utf-8'))['achievement']

        try:
            achievement = session.query(model.Achievement).get(id)
        except SQLAlchemyError:
            session.rollback()
            raise

        if achievement is None:
            req.context['result'] = {
                'errors': [{
                    'status': '404',
                    'title': 'Not Found',
                    'detail': 'Trofej s tímto ID neexistuje.'
                }]
            }
            resp.status = falcon.HTTP_404
            return

        achievement.title = data['title']
        achievement.picture = data['picture']
        achievement.description = data['description']
        if not data['persistent']:
            achievement.year = req.context['year']
        else:
            achievement.year = None

        try:
            session.commit()
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()

        self.on_get(req, resp, id)


class AchievementSuccessfulParticipant:
    def on_get(self, req, resp):
        trophy_id = successful_participant_trophy_id()

        if trophy_id is None:
            req.context['result'] = {
                'errors': [{
                    'status': '404',
                    'title': 'Not Found',
                    'detail': 'Successful trophy was not set'
                }]
            }

        return Achievement().on_get(req, resp, trophy_id)


class Achievements(object):

    def on_get(self, req, resp):
        try:
            achievements = session.query(model.Achievement).\
                filter(or_(model.Achievement.year == None,
                           model.Achievement.year == req.context['year'])).\
                all()
        except SQLAlchemyError:
            session.rollback()
            raise

        req.context['result'] = {
            'achievements': [util.achievement.to_json(achievement)
                             for achievement in achievements]
        }

    # Vytvoreni nove trofeje
    def on_post(self, req, resp):
        user = req.context['user']

        # Vytvoret novou trofej mohou jen orgove
        if (not user.is_logged_in()) or (not user.is_org()):
            req.context['result'] = {
                'errors': [{
                    'status': '401',
                    'title': 'Unauthorized',
                    'detail': 'Přidání trofeje může provést pouze organizátor.'
                }]
            }
            resp.status = falcon.HTTP_400
            return

        data = json.loads(req.stream.read().decode('utf-8'))['achievement']

        achievement = model.Achievement(
            title=data['title'],
            picture=data['picture'],
            description=data['description'],
        )
        if not data['persistent']:
            achievement.year = req.context['year']
        else:
            achievement.year = None

        try:
            session.add(achievement)
            session.commit()
        except SQLAlchemyError:
            session.rollback()
            raise

        req.context['result'] = {
            'achievement': util.achievement.to_json(achievement)
        }

        session.close()
