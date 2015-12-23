# -*- coding: utf-8 -*-

from db import session
import model
import util
import falcon
import json
import datetime

class TaskDeploy(object):

	"""
	Vraci JSON:
	{
		"result": "ok" | "error",
		"error": String
	}
	"""
	def on_post(self, req, resp, id):
		user = req.context['user']

		# Kontrola opravneni
		if (not user.is_logged_in()) or (not user.is_org()):
			req.context['result'] = { 'result': 'error', 'error': u'Nedostatečná oprávnění' }
			resp.status = falcon.HTTP_400
			return

		# Kontrola existence ulohy
		task = session.query(model.Task).get(id)
		if task is None:
			req.context['result'] = { 'result': 'error', 'error': u'Neexistující úloha' }
			resp.status = falcon.HTTP_404
			return

		# Zverejnene ulohy mohou deployovat pouze admini
		wave = session.query(model.Wave).get(task.wave)
		if (datetime.datetime.utcnow() > wave.time_published) and (not user.is_admin()):
			req.context['result'] = { 'result': 'error', 'error': u'Po zveřejnění úlohy může deploy provést pouze administrátor' }
			resp.status = falcon.HTTP_404
			return

		# TODO: magic
		# 1) git checkout task.git_branch
		# 2) git pull
		# 3) convert data to DB
		# 4) task.git_commit = last_commit_hash

		req.context['result'] = { 'result': 'ok' }
		resp.status = falcon.HTTP_200

