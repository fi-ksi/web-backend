# -*- coding: utf-8 -*-

from db import session
import model
import util
import falcon
import json
import datetime

class TaskMerge(object):

	"""
	Vraci JSON:
	{
		"result": "ok" | "error",
		"error": String
	}
	"""
	def on_post(self, req, resp, id):
		user = req.context['user']

		# Kontrola existence ulohy
		task = session.query(model.Task).get(id)
		if task is None:
			req.context['result'] = { 'result': 'error', 'error': u'Neexistující úloha' }
			resp.status = falcon.HTTP_404
			return

		if task.git_branch == "master":
			req.context['result'] = { 'result': 'error', 'error': u'Úloha je již ve větvi master' }
			resp.status = falcon.HTTP_404
			return

		wave = session.query(model.Wave).get(task.wave)

		# Kontrola opravneni
		if (not user.is_logged_in()) or ((not user.is_admin()) and (user.id != wave.garant)):
			req.context['result'] = { 'result': 'error', 'error': u'Nedostatečná oprávnění' }
			resp.status = falcon.HTTP_400
			return

		# Kontrola zamku
		lock = util.lock.git_locked()
		if lock:
			req.context['result'] = { 'result': 'error', 'error': u'GIT uzamčen zámkem '+lock }
			resp.status = falcon.HTTP_409
			return

		mergeLock = LockFile(util.admin.taskMerge.LOCKFILE)
		mergeLock.acquire(60) # Timeout zamku je 1 minuta

		# TODO: magic
		# 0) check if task.git_branch exists, check if task.git_path exists in the branch
		# 1) git diff task.git_branch master <- modified files in task.git_branch must be only in task.git_path directory
		# 2) git merge task.git_branch into "master"
		# 3) git close task_git_branch (close on origin too)
		# 4) git push
		# 5) task.git_branch = "master"
		# 6) task.git_commit = last_commit_hash

		try:
			pass
		except:
			raise
		finally:
			mergeLock.release()

		req.context['result'] = { 'result': 'ok' }
		resp.status = falcon.HTTP_200

