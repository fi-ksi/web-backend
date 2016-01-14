# -*- coding: utf-8 -*-
import json, falcon, os, magic, multipart
from sqlalchemy import func

import datetime
from db import session
from model import ModuleType
import model
import util


class Module(object):

	def on_get(self, req, resp, id):
		user = req.context['user']

		if not user.is_logged_in():
			resp.status = falcon.HTTP_400
			return

		module = session.query(model.Module).get(id)
		if module is None:
			resp.status = falcon.HTTP_404
		else:
			task = session.query(model.Task).get(module.task)
			if util.task.status(task, user) != util.TaskStatus.LOCKED:
				req.context['result'] = { 'module': util.module.to_json(module, user.id) }
			else:
				resp.status = falcon.HTTP_403


class ModuleSubmit(object):

	def _upload_files(self, req, module, user_id, resp):
		# Soubory bez specifikace delky neberem.
		if not req.content_length:
			resp.status = falcon.HTTP_411
			req.context['result'] = { 'result': 'error', 'error': 'Nelze nahrát neukončený stream.' }
			return

		# Prilis velke soubory neberem.
		if req.content_length > util.config.MAX_UPLOAD_FILE_SIZE:
			resp.status = falcon.HTTP_413
			req.context['result'] = { 'result': 'error', 'error': 'Maximální velikost dávky je 20 MB.' }
			return

		# Pokud uz existuji odevzdane soubory, nevytvarime nove
		# evaluation, pouze pripojujeme k jiz existujicimu
		existing = util.module.existing_evaluation(module.id, user_id)
		if len(existing) > 0:
			evaluation = session.query(model.Evaluation).get(existing[0])
			evaluation.time = datetime.datetime.utcnow()
			report = evaluation.full_report
		else:
			report = str(datetime.datetime.now()) + ' : === Uploading files for module id \'%s\' for task id \'%s\' ===\n' % (module.id, module.task)

			evaluation = model.Evaluation(user=user_id, module=module.id)
			try:
				session.add(evaluation)
				session.commit()
			except:
				session.rollback()
				raise

			# Lze uploadovat jen omezeny pocet souboru.
			file_cnt = session.query(model.SubmittedFile).\
				filter(model.SubmittedFile.evaluation == evaluation.id).count()
			if file_cnt > util.config.MAX_UPLOAD_FILE_COUNT:
				resp.status = falcon.HTTP_400
				req.context['result'] = { 'result': 'error', 'error': 'K řešení lze nahrát nejvýše 20 souborů.' }
				return

		dir = util.module.submission_dir(module.id, user_id)

		try:
			os.makedirs(dir)
		except OSError:
			pass

		if not os.path.isdir(dir):
			resp.status = falcon.HTTP_400
			req.context['result'] = { 'result': 'error', 'error': 'Chyba 42, kontaktuj orga.' }
			return

		files = multipart.MultiDict()
		content_type, options = multipart.parse_options_header(req.content_type)
		boundary = options.get('boundary', '')

		if not boundary:
			raise multipart.MultipartError("No boundary for multipart/form-data.")

		for part in multipart.MultipartParser(req.stream, boundary, req.content_length, 2**30, 2**20, 2**18, 2**16, 'utf-8'):
			path = '%s/%s' % (dir, part.filename)
			part.save_as(path)
			mime = magic.Magic(mime=True).from_file(path)

			report += str(datetime.datetime.now()) + ' :  [y] uploaded file: \'%s\' (mime: %s) to file %s\n' % (part.filename, mime, path)

			# Pokud je tento soubor jiz v databazi, zaznam znovu nepridavame
			file_in_db = session.query(model.SubmittedFile).\
				filter(model.SubmittedFile.evaluation == evaluation.id).\
				filter(model.SubmittedFile.path == path).scalar()

			if file_in_db is None:
				submitted_file = model.SubmittedFile(evaluation=evaluation.id, mime=mime, path=path)
				session.add(submitted_file)

		evaluation.full_report = report
		try:
			session.add(evaluation)
			session.commit()
		except:
			session.rollback()
			raise
		finally:
			session.close()

		req.context['result'] = { 'result': 'correct' }

	def _evaluate_code(self, req, module, user_id, resp, data):
		# Pokud neni modul autocorrrect, pridavame submitted_files
		# k jednomu evaluation.
		# Pokud je autocorrect, pridavame evaluation pro kazde vyhodnoceni souboru.
		existing = util.module.existing_evaluation(module.id, user_id)
		if (not module.autocorrect) and (len(existing) > 0):
			evaluation = session.query(model.Evaluation).get(existing[0])
			evaluation.time = datetime.datetime.utcnow()
		else:
			evaluation = model.Evaluation(user=user_id, module=module.id, full_report="")
			try:
				session.add(evaluation)
				session.commit()
			except:
				session.rollback()
				raise

		code = model.SubmittedCode(evaluation=evaluation.id, code=data)
		try:
			session.add(code)
			session.commit()
		except:
			session.rollback()
			raise

		if not module.autocorrect:
			try:
				session.commit()
			except:
				session.rollback()
				raise
			finally:
				session.close()
			req.context['result'] = {'result': 'correct'}
			return

		result, report, output = util.programming.evaluate(module.task, module, user_id, data)

		points = module.max_points if result == 'correct' else 0
		evaluation.points = points
		evaluation.full_report += str(datetime.datetime.now()) + " : " + report + '\n'

		try:
			session.commit()
		except:
			session.rollback()
			raise
		finally:
			session.close()

		req.context['result'] = {'result': result, 'score': points, 'output': output}

	def on_post(self, req, resp, id):
		user = req.context['user']

		if not user.is_logged_in():
			resp.status = falcon.HTTP_400
			return

		module = session.query(model.Module).get(id)

		if not module:
			resp.status = falcon.HTTP_404
			req.context['result'] = { 'result': 'error', 'error': u'Neexistující modul' }
			return

		# Po deadlinu nelze POSTovat reseni
		if session.query(model.Task).get(module.task).time_deadline < datetime.datetime.utcnow():
			req.context['result'] = { 'result': 'error', 'error': u'Nelze odevzdat po termínu odevzdání úlohy' }
			return

		if module.type == ModuleType.GENERAL:
			self._upload_files(req, module, user.id, resp)
			return

		data = json.loads(req.stream.read())['content']

		if module.type == ModuleType.PROGRAMMING:
			self._evaluate_code(req, module, user.id, resp, data)
			# ToDo: Auto actions
			return

		if module.type == ModuleType.QUIZ:
			result, report = util.quiz.evaluate(module.task, module, data)
		elif module.type == ModuleType.SORTABLE:
			result, report = util.sortable.evaluate(module.task, module, data)
		elif module.type == ModuleType.TEXT:
			result, report = util.text.evaluate(module.task, module, data)


		points = module.max_points if result else 0
		evaluation = model.Evaluation(user=user.id, module=module.id, points=points, full_report=report)
		req.context['result'] = {'result': 'correct' if result else 'incorrect', 'score': points}

		if "action" in report:
			util.module.perform_action(module, user)

		try:
			session.add(evaluation)
			session.commit()
		except:
			session.rollback()
			raise
		finally:
			session.close()

class ModuleSubmittedFile(object):

	def _get_submitted_file(self, req, resp, id):
		user = req.context['user']

		if not user.is_logged_in():
			resp.status = falcon.HTTP_403
			return None

		submittedFile = session.query(model.SubmittedFile).get(id)
		if submittedFile is None:
			resp.status = falcon.HTTP_404
			return None

		evaluation = session.query(model.Evaluation).get(submittedFile.evaluation)

		if evaluation.user == user.id or user.is_org:
			return submittedFile
		else:
			resp.status = falcon.HTTP_403
			return None

	def on_get(self, req, resp, id):
		submittedFile = self._get_submitted_file(req, resp, id)
		if submittedFile:
			path = submittedFile.path

			if not os.path.isfile(path):
				resp.status = falcon.HTTP_404
				return

			resp.content_type = magic.Magic(mime=True).from_file(path)
			resp.stream_len = os.path.getsize(path)
			resp.stream = open(path, 'rb')

	def on_delete(self, req, resp, id):
		submittedFile = self._get_submitted_file(req, resp, id)
		if submittedFile:
			# Kontrola casu (soubory lze mazat jen pred deadline)
			task = session.query(model.Task).\
				join(model.Module, model.Module.task == model.Task.id).\
				join(model.Evaluation, model.Evaluation.module == model.Module.id).\
				filter(model.Evaluation.id == submittedFile.evaluation).first()

			if task.time_deadline < datetime.datetime.utcnow():
				req.context['result'] = { 'result': 'error', 'error': u'Nelze smazat soubory po termínu odevzdání úlohy' }
				return

			try:
				os.remove(submittedFile.path)

				evaluation = session.query(model.Evaluation).get(submittedFile.evaluation)
				if evaluation:
					evaluation.full_report += str(datetime.datetime.now()) + " : removed file " + submittedFile.path + '\n'

				try:
					session.delete(submittedFile)
					session.commit()
				except:
					session.rollback()
					raise
				req.context['result'] = { 'status': 'ok' }

			except OSError:
				req.context['result'] = { 'status': 'error', 'error': u'Soubor se nepodařilo odstranit z filesystému' }
				return
			except SQLAlchemyError:
				req.context['result'] = { 'status': 'error', 'error': u'Záznam o souboru se nepodařilo odstranit z databáze' }
				return
		else:
			if resp.status == falcon.HTTP_404:
				req.context['result'] = { 'status': 'error', 'error': u'Soubor nenalezen na serveru' }
			elif resp.status == falcon.HTTP_403:
				req.context['result'] = { 'status': 'error', 'error': u'K tomuto souboru nemáte oprávnění' }
			else:
				req.context['result'] = { 'status': 'error', 'error': u'Soubor se nepodařilo získat' }
			resp.status = falcon.HTTP_200
