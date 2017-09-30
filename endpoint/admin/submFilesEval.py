import falcon
from sqlalchemy.exc import SQLAlchemyError
from zipfile import ZipFile
from io import BytesIO
import os

from db import session
import model
import util


class SubmFilesEval(object):

    def on_get(self, req, resp, eval_id):
        """ Vraci vsechny soubory daneho hodnoceni. """

        try:
            user = req.context['user']

            if (not user.is_logged_in()) or (not user.is_org()):
                resp.status = falcon.HTTP_400
                return

            inMemoryOutputFile = BytesIO()
            zipFile = ZipFile(inMemoryOutputFile, 'w')

            files = [
                r for (r, ) in
                session.query(model.SubmittedFile.path).
                filter(model.SubmittedFile.evaluation == eval_id).
                distinct()
            ]

            for fname in files:
                if os.path.isfile(fname):
                    zipFile.write(fname, os.path.basename(fname))

            zipFile.close()

            resp.set_header('Content-Disposition',
                            'inline; filename="eval_' + str(eval_id) + '.zip"')
            resp.content_type = "application/zip"
            resp.body = inMemoryOutputFile.getvalue()
            resp.stream_len = len(resp.body)

            inMemoryOutputFile.close()
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()
