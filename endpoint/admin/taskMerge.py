# -*- coding: utf-8 -*-

from db import session
import model, util, falcon, json, datetime, git
from lockfile import LockFile

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
			req.context['result'] = 'Neexistujici uloha'
			resp.status = falcon.HTTP_404
			return

		# Kontrola existence git_branch a git_path
		if (task.git_path is None) or (task.git_branch is None):
			req.context['result'] = 'Uloha nema zadanou gitovskou vetev nebo adresar'
			resp.status = falcon.HTTP_400
			return

		if task.git_branch == "master":
			req.context['result'] = 'Uloha je jiz ve vetvi master'
			resp.status = falcon.HTTP_400
			return

		wave = session.query(model.Wave).get(task.wave)

		# Merge mohou provadet pouze administratori a garant vlny
		if (not user.is_logged_in()) or ((not user.is_admin()) and (user.id != wave.garant)):
			req.context['result'] = 'Nedostatecna opravneni'
			resp.status = falcon.HTTP_400
			return

		# Kontrola zamku
		lock = util.lock.git_locked()
		if lock:
			req.context['result'] = 'GIT uzamcen zámkem '+lock + "\nNekdo momentalne provadi akci s gitem, opakujte prosim akci za 20 sekund."
			resp.status = falcon.HTTP_409
			return

		mergeLock = LockFile(util.admin.taskMerge.LOCKFILE)
		mergeLock.acquire(60) # Timeout zamku je 1 minuta

		# TODO: magic
		# DONE 0) check if task.git_branch exists, check if task.git_path exists in the branch
		# 1) git diff task.git_branch master <- modified files in task.git_branch must be only in task.git_path directory
		# 2) git merge task.git_branch into "master"
		# 3) git close task_git_branch (close on origin too)
		# 4) git push
		# 5) task.git_branch = "master"
		# 6) task.git_commit = last_commit_hash

		try:
			# Pull repozitare
			repo = git.Repo(util.git.GIT_SEMINAR_PATH)
			repo.remotes.origin.pull()

			if task.git_branch in repo.heads:
				repo.git.branch('-D', task.git_branch)

			task.git_branch = 'master'
			task.git_commit = repo.heads['master'].commit.hexsha

			session.commit()
		except:
			session.rollback()
			raise
		finally:
			mergeLock.release()

		resp.status = falcon.HTTP_200

