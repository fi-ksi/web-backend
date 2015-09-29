import os, time, uuid, magic

import falcon
from profile import ALLOWED_MIME_TYPES

from db import session
import model

class Image(object):

	def on_get(self, req, resp, context, id):
		if context == 'profile':
			user = session.query(model.User).filter(model.User.id == int(id)).first()

			if not user or not user.profile_picture:
				resp.status = falcon.HTTP_404
				return

			image = user.profile_picture
		else:
			resp.status = falcon.HTTP_400
			return

		resp.content_type = magic.Magic(mime=True).from_file(image)
		resp.stream_len = os.path.getsize(image)
		resp.stream = open(image, 'rb')
