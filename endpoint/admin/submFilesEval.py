import falcon

from db import session
import model
import util
from zipfile import ZipFile
from StringIO import StringIO
import unicodedata
import os

class SubmFilesEval(object):

	# Vraci vsechny soubory daneho hodnoceni.
	def on_get(self, req, resp, eval_id):
		user = req.context['user']

		#if (not user.is_logged_in()) or (not user.is_org()):
		#	resp.status = falcon.HTTP_400
		#	return

		inMemoryOutputFile = StringIO()
		zipFile = ZipFile(inMemoryOutputFile, 'w')

		files = [ r for (r, ) in session.query(model.SubmittedFile.path).\
			filter(model.SubmittedFile.evaluation == eval_id).distinct() ]

		for fname in files:
			if os.path.isfile(fname):
				zipFile.write(fname, os.path.basename(fname))

		zipFile.close()

		resp.set_header('Content-Disposition', "inline; filename=\"eval_" + str(eval_id) + ".zip\"")
		resp.content_type = "application/zip"
		resp.stream_len = inMemoryOutputFile.len
		resp.body = inMemoryOutputFile.getvalue()

		inMemoryOutputFile.close()

