import tempfile

import falcon
import magic
import multipart
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError

import model
from db import session
from shutil import move

ALLOWED_MIME_TYPES = ('application/pdf',)
UPLOAD_DIR = Path().joinpath('data').joinpath('diplomas')


def get_diploma_path(year_id: int, user_id: int) -> Path:
    return UPLOAD_DIR.joinpath(f"year_{year_id}").joinpath(f"user_{user_id}.pdf")


class DiplomaGrant:
    def on_post(self, req, resp, id):
        try:
            userinfo = req.context['user']

            if not userinfo.is_logged_in() or not userinfo.is_admin():
                resp.status = falcon.HTTP_401
                req.context['result'] = {
                    'result': 'error',
                    'error': 'Nahravat diplomy muze pouze admin.'
                }
                return

            if req.context['year_obj'].sealed:
                resp.status = falcon.HTTP_403
                req.context['result'] = {
                    'errors': [{
                        'status': '403',
                        'title': 'Forbidden',
                        'detail': 'Ročník zapečetěn.'
                    }]
                }
                return

            content_type, options = multipart.parse_options_header(
                req.content_type
            )
            boundary = options.get('boundary', '')

            if not boundary:
                raise multipart.MultipartError("No boundary for "
                                               "multipart/form-data.")

            for part in multipart.MultipartParser(req.stream, boundary,
                                                  req.content_length):
                file = part  # take only the first file
                break
            else:
                resp.status = falcon.HTTP_400
                req.context['result'] = {
                    'errors': [{
                        'status': '400',
                        'title': 'Bad Request',
                        'detail': 'No file found in the data'
                    }]
                }
                return

            user_id = id
            year_id = req.context['year_obj'].id
            tmpfile = tempfile.NamedTemporaryFile(delete=False)

            file.save_as(tmpfile.name)

            mime = magic.Magic(mime=True).from_file(tmpfile.name)

            if mime not in ALLOWED_MIME_TYPES:
                resp.status = falcon.HTTP_400
                req.context['result'] = {
                    'errors': [{
                        'status': '403',
                        'title': 'Forbidden',
                        'detail': f'Allowed file types are {ALLOWED_MIME_TYPES}'
                    }]
                }
                return

            target_file = get_diploma_path(year_id, user_id)

            try:
                target_file.parent.mkdir(parents=True, exist_ok=True, mode=0o750)
            except OSError:
                print('Unable to create directory for profile pictures')
                resp.status = falcon.HTTP_500
                return

            try:
                move(tmpfile.name, target_file)
            except OSError:
                print('Unable to remove temporary file %s' % tmpfile.name)

            diploma = model.Diploma(
                user_id=user_id,
                year_id=year_id
            )
            session.add(diploma)

            session.commit()

            req.context['result'] = {}
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()
