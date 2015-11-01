import os, time, uuid, magic

import falcon

from db import session
import model
import util

class Content(object):

	def on_get(self, req, resp):
		
		filePath = 'data/' + req.path.replace('..', '');

		if not os.path.isfile(filePath):
			resp.status = falcon.HTTP_400
			return

		resp.content_type = magic.Magic(mime=True).from_file(filePath)
		resp.stream_len = os.path.getsize(filePath)
		resp.stream = open(filePath, 'rb')
