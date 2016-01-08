from db import session
import model
import util
import falcon
import json
import datetime
from lockfile import LockFile

class Task(object):

	def on_get(self, req, resp, id):
		user = req.context['user']
		task = session.query(model.Task).get(id)

		# task_admin mohou ziskat jen orgove
		if (not user.is_logged_in()) or (not user.is_org()):
			resp.status = falcon.HTTP_400
			return

		if task is None:
			resp.status = falcon.HTTP_404
			return

		wave = session.query(model.Wave).get(task.wave)
		req.context['result'] = { 'atask': util.task.admin_to_json(task, user, wave) }

	# UPDATE ulohy
	def on_put(self, req, resp, id):
		user = req.context['user']
		data = json.loads(req.stream.read())['atask']
		wave = session.query(model.Wave).get(data['wave'])

		if wave is None:
			resp.status = falcon.HTTP_404
			return

		if (not user.is_logged_in()) or ((not user.is_admin()) and (user.id != wave.garant)):
			resp.status = falcon.HTTP_400
			return

		try:
			task = session.query(model.Task).get(id)
			if task is None:
				resp.status = falcon.HTTP_404
				return

			# Ulohu lze editovat jen pred casem zverejneni vlny
			wave = session.query(model.Wave).get(task.wave)
			if (datetime.datetime.utcnow() > wave.time_published) and (not user.is_admin()):
				resp.status = falcon.HTTP_403
				return

			task.title = data['title']
			task.git_path = data['git_path']
			task.git_branch = data['git_branch']
			task.git_commit = data['git_commit']

			session.commit()
		except:
			session.rollback()
			raise
		finally:
			session.close()

		self.on_get(req, resp, id)

	# Smazani ulohy
	def on_delete(self, req, resp, id):
		user = req.context['user']

		# Ulohu mohou smazat jen admini
		if (not user.is_logged_in()) or (not user.is_admin()):
			resp.status = falcon.HTTP_400
			return

		try:
			task = session.query(model.Task).get(id)
			if task is None:
				resp.status = falcon.HTTP_404
				return

			# Ulohu lze smazat jen pred casem zverejneni vlny
			wave = session.query(model.Wave).get(task.wave)
			if datetime.datetime.utcnow() > wave.time_published:
				resp.status = falcon.HTTP_403
				return

			# Nejprve odstranime diskuzni vlakno
			thread = session.query(model.Thread).get(task.thread)
			if thread is not None:
				session.delete(thread)
				session.commit()

			# Pak odstranime vsechny moduly
			for module in task.modules:
				print module
				util.module.delete_module(module)

			if task.prerequisite_obj:
				util.prerequisite.remove_tree(task.prerequisite_obj, True)

			session.delete(task)
			session.commit()
		except:
			session.rollback()
			raise
		finally:
			session.close()

###############################################################################

class Tasks(object):

	def on_get(self, req, resp):
		user = req.context['user']
		wave = req.get_param_as_int('wave')

		# Zobrazovat task_admin mohou jen orgove
		if (not user.is_logged_in()) or (not user.is_org()):
			resp.status = falcon.HTTP_400
			return

		tasks = session.query(model.Task, model.Wave).join(model.Wave, model.Task.wave == model.Wave.id)
		if wave is None:
			tasks = tasks.filter(model.Wave.year == req.context['year'])
		else:
			tasks = tasks.filter(model.Wave.id == wave)
		tasks = tasks.all()

		req.context['result'] = { 'atasks': [ util.task.admin_to_json(task.Task, user, task.Wave) for task in tasks ] }

	# Vytvoreni nove ulohy
	"""
	Specifikace POST pozadavku: ?create_git=(true|false)
	{
		"task": {
			"wave": Integer, <- id vlny
			"title": String,
			"author": Integer, <- id autora
			"git_path": String, <- adresar ulohy v GITu vcetne cele cesty
			"git_branch": String, <- nazev gitove vetve, ve ktere vytvorit ulohu / ze ktere cerpat data pro deploy
			"git_commit" String <- hash posledniho commitu, pokud je ?create_git=true, nevyplnuje se
		}
	}
	"""
	def on_post(self, req, resp):
		user = req.context['user']
		year = req.context['year']
		data = json.loads(req.stream.read())['atask']
		wave = session.query(model.Wave).get(data['wave'])

		if wave is None:
			resp.status = falcon.HTTP_404
			return

		# Vytvorit novou ulohu mohou jen admini nebo garanti vlny.
		if (not user.is_logged_in()) or ((not user.is_admin()) and (user.id != wave.garant)):
			resp.status = falcon.HTTP_400
			return

		# Ulohu lze vytvorit jen pred casem zverejneni vlny
		if datetime.datetime.utcnow() > wave.time_published:
			resp.status = falcon.HTTP_403
			return

		# Vytvoreni adresare v repu je option
		print req.get_param_as_bool('create_git')
		if req.get_param_as_bool('create_git'):
			print "Creating git"
			# Kontrola zamku
			lock = util.lock.git_locked()
			if lock:
				resp.status = falcon.HTTP_409
				return

			newLock = LockFile(util.admin.task.LOCKFILE)
			newLock.acquire(60) # Timeout zamku je 1 minuta

			try:
				git_commit = util.admin.task.createGit(data['git_path'], data['git_branch'], data['author'], data['title'])
			except:
				raise
			finally:
				newLock.release()
		else:
			git_commit = data['git_commit'] if 'git_commit' in data else None

		try:
			# Nejprve vytvorime nove diskuzni vlakno
			taskThread = model.Thread(
				title = data['title'],
				public = True,
				year = req.context['year']
			)
			session.add(taskThread)
			session.commit()

			# Pote vytvorime ulohu
			task = model.Task(
				wave = data['wave'],
				title = data['title'],
				author = data['author'],
				git_path = data['git_path'],
				git_branch = data['git_branch'],
				git_commit = git_commit,
				thread = taskThread.id
			)

			session.add(task)
			session.commit()
		except:
			session.rollback()
			raise

		req.context['result'] = { 'atask': util.task.admin_to_json(task, user, wave) }

		session.close()
