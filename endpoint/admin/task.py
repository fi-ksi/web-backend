from db import session
import model
import util
import falcon
import json
import datetime

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

		req.context['result'] = { 'task': util.task.admin_to_json(task) }

	# UPDATE ulohy
	def on_put(self, req, resp, id):
		user = req.context['user']
		data = json.loads(req.stream.read())['task']
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
			if datetime.datetime.utcnow() > wave.time_published:
				resp.status = falcon.HTTP_403
				return

			task.title = data['title']
			task.git_path = data['git_path']

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

		tasks = session.query(model.Task)
		if wave is None:
			tasks = tasks.join(model.Wave, model.Wave.id == model.Task.wave).\
				filter(model.Wave.year == req.context['year'])
		else:
			tasks = tasks.filter(model.Task.wave == wave)
		tasks = tasks.all()

		req.context['result'] = { 'tasks': [ util.task.admin_to_json(task) for task in tasks ] }

	# Vytvoreni nove ulohy
	def on_post(self, req, resp):
		user = req.context['user']
		year = req.context['year']
		data = json.loads(req.stream.read())['task']
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
				git_path = data['git_path'],
				thread = taskThread.id
			)

			session.add(task)
			session.commit()
		except:
			session.rollback()
			raise

		req.context['result'] = { 'task': util.task.admin_to_json(task) }

		session.close()

