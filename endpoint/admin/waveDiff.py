from db import session
import model, util, falcon, json, datetime, git, os

class WaveDiff(object):

	def on_post(self, req, resp, id):
		user = req.context['user']

		if (not user.is_logged_in()) or (not user.is_org()):
			resp.status = falcon.HTTP_400
			return

		# Pull repozitare
		repo = git.Repo(util.git.GIT_SEMINAR_PATH)
		repo.remotes.origin.pull()

		try:
			# Ulohy ve vlne
			tasks = session.query(model.Task).\
				filter(model.Task.wave == id).all()

			# Diffujeme adresare uloh task.git_commit oproti HEAD
			for task in tasks:
				if (not task.git_branch) or (not task.git_path) or (not task.git_commit):
					task.deploy_status = 'default'
					continue

				# Checkout vetve ve ktere je uloha
				repo.git.checkout(task.git_branch)

				# Kontrola existence adresare ulohy
				if os.path.isdir(util.git.GIT_SEMINAR_PATH+task.git_path):
					hcommit = repo.head.commit
					diff = hcommit.diff(task.git_commit, paths=[task.git_path])
					if len(diff) > 0: task.deploy_status = 'diff'
				else:
					task.deploy_status = 'default'

			session.commit()
		except:
			session.rollback()
			raise
		finally:
			session.close()


