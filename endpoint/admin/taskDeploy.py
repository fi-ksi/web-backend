# -*- coding: utf-8 -*-

from db import session, _session
from sqlalchemy.exc import SQLAlchemyError
from lockfile import LockFile
import model, util, falcon, json, datetime, threading, os, re
from sqlalchemy.orm import scoped_session

class TaskDeploy(object):

	"""
	Vraci JSON:
	{
		"result": "ok" | "error",
		"error": String
	}
	"""
	def on_post(self, req, resp, id):
		try:
			user = req.context['user']

			# Kontrola opravneni
			if (not user.is_logged_in()) or (not user.is_org()):
				req.context['result'] = 'Nedostatecna opravneni'
				resp.status = falcon.HTTP_400
				return

			# Kontrola existence ulohy
			task = session.query(model.Task).get(id)
			if task is None:
				req.context['result'] = 'Neexistujici uloha'
				resp.status = falcon.HTTP_404
				return

			# Zverejnene ulohy mohou deployovat pouze admini
			wave = session.query(model.Wave).get(task.wave)
			if (datetime.datetime.utcnow() > wave.time_published) and (not user.is_admin()):
				req.context['result'] = 'Po zverejneni ulohy muze deploy provest pouze administrator'
				resp.status = falcon.HTTP_404
				return

			# Kontrola existence gitovske vetve a adresare v databazi
			if (task.git_branch is None) or (task.git_path is None):
				req.context['result'] = 'Uloha nema zadanou gitovskou vetev nebo adresar'
				resp.status = falcon.HTTP_400
				return

			# Kontrola zamku
			lock = util.lock.git_locked()
			if lock:
				req.context['result'] = 'GIT uzamcen zamkem ' + lock + "\nNekdo momentalne provadi akci s gitem, opakujte prosim akci za 20 sekund."
				resp.status = falcon.HTTP_409
				return

			# Stav na deploying je potreba nastavit v tomto vlakne
			task.deploy_status = 'deploying'
			session.commit()

			try:
				deployLock = LockFile(util.admin.taskDeploy.LOCKFILE)
				deployLock.acquire(60) # Timeout zamku je 1 minuta
				deployThread = threading.Thread(target=util.admin.taskDeploy.deploy, args=(task.id, deployLock, scoped_session(_session)), kwargs={})
				deployThread.start()
			finally:
				deployLock.release()

			resp.status = falcon.HTTP_200
		except SQLAlchemyError:
			session.rollback()
			raise
		finally:
			session.close()

	"""
	Vraci JSON:
	{
		"id": task_id,
		"log": String,
		"deploy_date": Datetime,
		"deploy_status": model.task.deploy_status
	}
	"""
	def on_get(self, req, resp, id):
		try:
			user = req.context['user']

			# Kontrola opravneni
			if (not user.is_logged_in()) or (not user.is_org()):
				resp.status = falcon.HTTP_400
				return

			status = {}

			task = session.query(model.Task).get(id)
			if task is None:
				resp.status = falcon.HTTP_404
				return

			log = None
			if os.path.isfile(util.admin.taskDeploy.LOGFILE):
				with open(util.admin.taskDeploy.LOGFILE, 'r') as f:
					data = f.readlines()
				if re.search(r"^(\d*)", data[0]).group(1) == str(id): log = ''.join(data[1:])

			status = {
				'id': task.id,
				'log': log,
				'deploy_date': task.deploy_date.isoformat() if task.deploy_date else None,
				'deploy_status': task.deploy_status
			}

			req.context['result'] = status
		except SQLAlchemyError:
			session.rollback()
			raise
		finally:
			session.close()

