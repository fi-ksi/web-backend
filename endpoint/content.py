import os, time, uuid, magic

import falcon

from db import session
import model
import util

class Content(object):

	def on_get(self, req, resp):
		
		print req.path

		# filePath = 'data/content' + address.replace('..', '');

		# if not os.path.isfile(filePath):
		# 	resp.status = falcon.HTTP_400
		# 	return

		# resp.content_type = magic.Magic(mime=True).from_file(filePath)
		# resp.stream_len = os.path.getsize(filePath)
		# resp.stream = open(filePath, 'rb')