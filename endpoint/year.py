# -*- coding: utf-8 -*-

from db import session
from sqlalchemy.exc import SQLAlchemyError
import model
import util
import json
import falcon

class Year(object):

    def on_get(self, req, resp, id):
        try:
            year = session.query(model.Year).get(id)

            if year is None:
                resp.status = falcon.HTTP_404
                return

            req.context['result'] = { 'year': util.year.to_json(year) }
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()

    # UPDATE rocniku
    def on_put(self, req, resp, id):
        try:
            user = req.context['user']

            # Upravovat rocniky mohou jen ADMINI
            if (not user.is_logged_in()) or (not user.is_admin()):
                resp.status = falcon.HTTP_400
                return

            data = json.loads(req.stream.read().decode('utf-8'))['year']

            year = session.query(model.Year).get(id)
            if year is None:
                resp.status = falcon.HTTP_404
                return

            year.id = data['index']
            year.year = data['year']
            year.sealed = data['sealed']
            year.point_pad = data['point_pad']

            # Aktualizace aktivnich orgu
            orgs = session.query(model.ActiveOrg).\
                filter(model.ActiveOrg.year == year.id).all()

            for i in range(len(orgs)-1, -1, -1):
                if str(orgs[i].org) in data['active_orgs']:
                    data['active_orgs'].remove(str(orgs[i].org))
                    del orgs[i]

            for org in orgs: session.delete(org)

            for user_id in data['active_orgs']:
                org = model.ActiveOrg(org=user_id, year=year.id)
                session.add(org)

            session.commit()
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()

        self.on_get(req, resp, id)

    # Smazani rocniku
    def on_delete(self, req, resp, id):
        try:
            user = req.context['user']

            if (not user.is_logged_in()) or (not user.is_admin()):
                resp.status = falcon.HTTP_400
                return

            year = session.query(model.Year).get(id)
            if year is None:
                resp.status = falcon.HTTP_404
                return

            # Odstranit lze jen neprazdny rocnik
            waves_cnt = session.query(model.Wave).filter(model.Wave.year == year.id).count()
            if waves_cnt > 0:
                resp.status = falcon.HTTP_403
                return

            session.delete(year)
            session.commit()
            req.context['result'] = {}
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()

###############################################################################

class Years(object):

    def on_get(self, req, resp):
        try:
            years = session.query(model.Year).all()

            sum_points = util.task.max_points_year_dict()

            req.context['result'] = { 'years': [ util.year.to_json(year, sum_points[year.id]) for year in years ] }
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()

    # Vytvoreni noveho rocniku
    def on_post(self, req, resp):
        try:
            user = req.context['user']

            # Vytvoret novy rocnik mohou jen ADMINI
            if (not user.is_logged_in()) or (not user.is_admin()):
                resp.status = falcon.HTTP_400
                return

            data = json.loads(req.stream.read().decode('utf-8'))['year']

            year = model.Year(
                id = data['index'],
                year = data['year'],
                sealed = data['sealed'] if data['sealed'] else False,
                point_pad = data['point_pad']
            )

            session.add(year)
            session.commit()

            if 'active_orgs' in data:
                for user_id in data['active_orgs']:
                    org = model.ActiveOrg(org=user_id, year=year.id)
                    session.add(org)

            session.commit()

            req.context['result'] = { 'year': util.year.to_json(year) }

        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()

