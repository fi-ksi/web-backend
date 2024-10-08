import os
import magic
import falcon
from sqlalchemy.exc import SQLAlchemyError

from .profile import ALLOWED_MIME_TYPES
from db import session
import model
import util


class Image(object):

    def on_get(self, req, resp, context, id):
        if context == 'profile':
            try:
                user = session.query(model.User).\
                    filter(model.User.id == int(id)).\
                    first()
            except SQLAlchemyError:
                session.rollback()
                raise

            if not user or not user.profile_picture:
                resp.status = falcon.HTTP_404
                return

            image = user.profile_picture
        elif context == 'codeExecution':
            try:
                execution = session.query(model.CodeExecution).get(id)
            except SQLAlchemyError:
                session.rollback()
                raise

            if not execution:
                resp.status = falcon.HTTP_400
                return

            if not req.get_param('file'):
                resp.status = falcon.HTTP_400
                return

            image = os.path.join(
                util.programming.code_execution_dir(execution.user, execution.module),
                os.path.basename(req.get_param('file')))

        elif context == 'codeModule':
            if not req.get_param('file') or not req.get_param('module') or not req.get_param('user'):
                resp.status = falcon.HTTP_400
                return

            user_id = int(req.get_param('user'))
            module_id = int(req.get_param('module'))
            filename: str = os.path.basename(req.get_param('file'))

            if not filename.endswith(".png"):
                resp.status = falcon.HTTP_400
                return

            image = os.path.join(
                util.programming.code_execution_dir(user_id, module_id),
                filename
                )
            
            resp.cache_control = ('no-cache', )

        else:
            resp.status = falcon.HTTP_400
            return

        if not os.path.isfile(image):
            resp.status = falcon.HTTP_400
            return

        resp.content_type = magic.Magic(mime=True).from_file(image)
        resp.stream = open(image, 'rb', os.path.getsize(image))
