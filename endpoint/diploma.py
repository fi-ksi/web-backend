import os

import falcon
import magic

import model
from db import session
from endpoint.admin.diploma import get_diploma_path
from util.config import backend_url


class Diploma:
    def on_get(self, req, resp, user):
        diplomas = session.query(model.Diploma)\
            .filter(model.Diploma.user_id == user)

        req.context['result'] = {
            'diplomas': [{
                'year': diploma.year_id,
                'revoked': diploma.revoked,
                'url': f"{backend_url()}/diplomas/{user}/{diploma.year_id}/show"
            } for diploma in diplomas]
        }


class DiplomaDownload:
    def on_get(self, req, resp, user, year):
        user_id = user
        year_id = year

        diploma = session.query(model.Diploma)\
            .filter(model.Diploma.user_id == user_id, model.Diploma.year_id == year_id).first()

        if diploma is None:
            resp.status = falcon.HTTP_404
            req.context['result'] = {
                'errors': [{
                    'status': '404',
                    'title': 'Not found',
                    'detail': 'No diploma for this user & year combination found'
                }]
            }
            return

        path = get_diploma_path(year_id, user_id)
        resp.content_type = magic.Magic(mime=True).from_file(f"{path}")
        resp.stream_len = os.path.getsize(path)
        resp.stream = open(path, 'rb')
