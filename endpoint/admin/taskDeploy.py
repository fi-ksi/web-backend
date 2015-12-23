# -*- coding: utf-8 -*-

from db import session
from lockfile import LockFile
import model
import util
import falcon
import json
import datetime
import threading

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

		if (task.git_branch is None) or (task.git_path is None):
			req.context['result'] = { 'result': 'error', 'error': u'Úloha nemá zadanou gitovskou větev nebo adresář' }
			resp.status = falcon.HTTP_400
			return

		deployLock = LockFile(util.admin.taskDeploy.LOCKFILE)
		if deployLock.is_locked():
			req.context['result'] = { 'result': 'error', 'error': u'Deploy již probíhá' }
			resp.status = falcon.HTTP_400
			return

		deployLock.acquire(60) # Timeout zamku je 1 minuta
		deployThread = threading.Thread(target=util.admin.taskDeploy.deploy, args=(task, deployLock), kwargs={})
		deployThread.start()

		req.context['result'] = { 'result': 'ok' }
		resp.status = falcon.HTTP_200

