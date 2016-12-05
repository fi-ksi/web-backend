# -*- coding: utf-8 -*-

import os, time, uuid, magic

import falcon
from profile import ALLOWED_MIME_TYPES

from db import session
from sqlalchemy.exc import SQLAlchemyError
import model
import util

class Image(object):

    def on_get(self, req, resp, context, id):
        if context == 'profile':
            try:
                user = session.query(model.User).filter(model.User.id == int(id)).first()
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

            image = os.path.join(util.programming.code_execution_dir(execution.id), os.path.basename(req.get_param('file')))
        else:
            resp.status = falcon.HTTP_400
            return

        if not os.path.isfile(image):
            resp.status = falcon.HTTP_400
            return

        resp.content_type = magic.Magic(mime=True).from_file(image)
        resp.stream_len = os.path.getsize(image)
        resp.stream = open(image, 'rb')
