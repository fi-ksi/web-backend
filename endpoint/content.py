import os
import magic
import multipart
from typing import Optional
from pathlib import Path

import falcon
from falcon.request import datetime

import model
import util
from db import session
from util.logger import audit_log
from util.task import time_published


class Content(object):

    # Smaze adresarovou strukturu rekurzivne od nejvic zanoreneho
    #  dokud jsou adresare prazdne.
    def _delete_tree(self, path):
        if os.listdir(path):
            return
        try:
            os.rmdir(path)
            self._delete_tree(os.path.dirname(path))
        except Exception:
            return

    # GET na content vraci
    # a) soubor, pokud je v \path cesta k souboru,
    # b) obsah adresare, pokud je v \path cesta k adresari.
    def on_get(self, req, resp):
        if req.get_param('path'):
            short_path = req.get_param('path').replace('..', '')
        else:
            short_path = "."
        file_path = str(self.__parse_short_path(req, resp, req.context['user']))
        if not file_path:
            return

        if os.path.isdir(file_path):
            req.context['result'] = {
                'content': util.content.dir_to_json(short_path)
            }
            return

        if not os.path.isfile(file_path):
            req.context['result'] = {
                'content': util.content.empty_content(short_path)
            }
            return

        resp.content_type = magic.Magic(mime=True).from_file(file_path)
        resp.set_stream(open(file_path, 'rb'), os.path.getsize(file_path))

    def on_post(self, req, resp):
        user = req.context['user']

        if (not user.is_logged_in()) or (not user.is_org()):
            req.context['result'] = {
                'errors': [{
                    'status': '401',
                    'title': 'Unauthorized',
                    'detail': 'Upravovat content může pouze organizátor.'
                }]
            }
            resp.status = falcon.HTTP_400
            return

        dir_path = str(self.__parse_short_path(req, resp, user))
        if dir_path is None:
            return

        if not req.content_length:
            resp.status = falcon.HTTP_411
            return

        if req.content_length > util.config.MAX_UPLOAD_FILE_SIZE:
            resp.status = falcon.HTTP_413
            return

        files = multipart.MultiDict()
        content_type, options = multipart.parse_options_header(
            req.content_type)
        boundary = options.get('boundary', '')

        if not boundary:
            raise multipart.MultipartError(
                "No boundary for multipart/form-data.")

        try:
            if not os.path.isdir(dir_path):
                os.makedirs(dir_path)

            for part in multipart.MultipartParser(
                    req.stream, boundary, req.content_length,
                    2**30, 2**20, 2**18, 2**16, 'utf-8'):
                path = '%s/%s' % (dir_path, part.filename)
                part.save_as(path)
        except Exception:
            resp.status = falcon.HTTP_500
            raise

        req.context['result'] = {}
        resp.status = falcon.HTTP_200

    def on_delete(self, req, resp):
        user = req.context['user']

        if (not user.is_logged_in()) or (not user.is_org()):
            resp.status = falcon.HTTP_400
            return

        file_path = self.__parse_short_path(req, resp, user)
        if not file_path:
            return

        if not os.path.isfile(file_path):
            resp.status = falcon.HTTP_404
            return

        try:
            os.remove(file_path)
            self._delete_tree(os.path.dirname(file_path))
        except Exception:
            resp.status = falcon.HTTP_500
            raise

        resp.status = falcon.HTTP_200
        req.context['result'] = {}

    @staticmethod
    def __parse_short_path(req, resp, user) -> Optional[Path]:
        path_base = (Path('data') / 'content').absolute()

        if req.get_param('path'):
            short_path = req.get_param('path')
        else:
            short_path = "."

        file_path = (path_base / Path(short_path)).absolute()
        if not file_path.is_relative_to(path_base):
            audit_log(
                scope="HACK",
                user_id=user.id if user.is_logged_in() else None,
                message=f"Attempt to access content outside box",
                message_meta={
                    'path': short_path
                }
            )
            resp.status = falcon.HTTP_404
            return None
        return file_path


class TaskContent(object):

    def on_get(self, req, resp, id, view):
        user = req.context['user']

        # TODO: Enable after frontend is sending auth token in headers
        # if time_published(id) > datetime.now() and not user.is_org() and not user.is_tester():
        #     req.context['result'] = {
        #         'errors': [{
        #             'status': '403',
        #             'title': 'Forbidden',
        #             'detail': 'Obsah úlohy ještě nebyl zveřejněn.'
        #         }]
        #     }
        #     resp.status = falcon.HTTP_403
        #     return

        if (view != 'icon' and not view.startswith('reseni')
                and not view.startswith('zadani')):
            resp.status = falcon.HTTP_400
            return

        path_param = req.get_param('path')
        if path_param is None:
            resp.status = falcon.HTTP_400
            return

        base_path = (Path('data') / 'task-content' / Path(str(id)).name / Path(view).name).absolute()
        file_path = (base_path / path_param).absolute()
        if not file_path.is_relative_to(base_path):
            resp.status = falcon.HTTP_404
            audit_log(
                scope="HACK",
                user_id=user.id if user.is_logged_in() else None,
                message=f"Attempt to access task content outside box",
                message_meta={
                    'id': id,
                    'view': view,
                    'path': path_param
                }
            )
            return

        if not os.path.isfile(file_path):
            resp.status = falcon.HTTP_404
            return

        resp.content_type = magic.Magic(mime=True).from_file(file_path)
        resp.set_stream(open(file_path, 'rb'), os.path.getsize(file_path))
