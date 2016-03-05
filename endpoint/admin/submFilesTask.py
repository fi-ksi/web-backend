# -*- coding: utf-8 -*-

import falcon

from db import session
import model
import util
from zipfile import ZipFile
from StringIO import StringIO
import unicodedata
import os

class SubmFilesTask(object):

	# Vraci vsechny soubory vsech resitelu pro danou ulohu.
	def on_get(self, req, resp, task_id):
		user = req.context['user']

		if (not user.is_logged_in()) or (not user.is_org()):
			resp.status = falcon.HTTP_400
			return

		inMemoryOutputFile = StringIO()
		zipFile = ZipFile(inMemoryOutputFile, 'w')

		modules = session.query(model.Module).\
			filter(model.Module.task == task_id).all()

		for module in modules:
			users = session.query(model.User).\
				join(model.Evaluation, model.Evaluation.user == model.User.id).\
				filter(model.Evaluation.module == module.id).all()

			for user in users:
				files = [ r for (r, ) in session.query(model.SubmittedFile.path).\
					join(model.Evaluation, model.Evaluation.id == model.SubmittedFile.evaluation).\
					filter(model.Evaluation.user == user.id, model.Evaluation.module == module.id).distinct() ]
				userdir = ("module_" + str(module.id) + "/" + util.submissions.strip_accents(user.first_name) + "_" + util.submissions.strip_accents(user.last_name)).replace(' ', '_')

				for fname in files:
					if os.path.isfile(fname):
						zipFile.write(fname, userdir + "/" + os.path.basename(fname))

		zipFile.close()

		resp.set_header('Content-Disposition', "inline; filename=\"task_" + str(task_id) + ".zip\"")
		resp.content_type = "application/zip"
		resp.stream_len = inMemoryOutputFile.len
		resp.body = inMemoryOutputFile.getvalue()

		inMemoryOutputFile.close()

