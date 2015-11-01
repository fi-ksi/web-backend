import json, falcon, os, magic, multipart
from sqlalchemy import func

from db import session
from model import ModuleType
import model
import util

def _module_to_json(module):
	return {'id': module.id, 'type': module.type, 'name': module.name, 'description': module.description}

class Module(object):

	def on_get(self, req, resp, id):
		user = req.context['user']

		if not user.is_logged_in():
			resp.status = falcon.HTTP_400
			return

		module = session.query(model.Module).get(id)
		module_json = _module_to_json(module)
		count = session.query(model.Evaluation.points).filter(model.Evaluation.user == user.id, model.Evaluation.module == id).count()

		if count > 0:
			status = session.query(func.max(model.Evaluation.points).label('points')).\
				filter(model.Evaluation.user == user.id, model.Evaluation.module == id).first()
			module_json['state'] = 'correct' if status.points == module.max_points else 'incorrect'
		else:
			module_json['state'] = 'blank'

		if module.type == ModuleType.PROGRAMMING:
			code = util.programming.build(module.id)
			module_json['code'] = code
			module_json['default_code'] = code
		elif module.type == ModuleType.QUIZ:
			module_json['questions'] = util.quiz.build(module.id)
		elif module.type == ModuleType.SORTABLE:
			module_json['sortable_list'] = util.sortable.build(module.id)
		elif module.type == ModuleType.GENERAL:
			module_json['state'] = 'correct' if count > 0 else 'blank'
			
			submittedFiles = session.query(model.SubmittedFile).\
				join(model.SubmittedFile.evaluation).\
				filter(model.Evaluation.user == user.id, model.Evaluation.module == id)
			
			module_json['submitted_files'] = [{'id': inst.id, 'filename': os.path.basename(inst.path)} for inst in submittedFiles]
		elif module.type == ModuleType.TEXT:
			module_json['fields'] = util.text.num_fields(module.id) 

		req.context['result'] = {'module': module_json}


class ModuleSubmit(object):

	def _upload_files(self, req, module, user_id, resp):
		report = '=== Uploading files for module id \'%s\' for task id \'%s\' ===\n\n' % (module.id, module.task)

		evaluation = model.Evaluation(user=user_id, module=module.id)
		session.add(evaluation)
		session.commit()

		dir = util.module.submission_dir(module.id, user_id)

		try:
			os.makedirs(dir)
		except OSError:
			pass

		if not os.path.isdir(dir):
			resp.status = falcon.HTTP_400
			req.context['result'] = {'result': 'incorrect'}
			return

		files = multipart.MultiDict()
		content_type, options = multipart.parse_options_header(req.content_type)
		boundary = options.get('boundary', '')

		if not boundary:
			raise multipart.MultipartError("No boundary for multipart/form-data.")

		for part in multipart.MultipartParser(req.stream, boundary, req.content_length):
			path = '%s/%d_%s' % (dir, evaluation.id, part.filename)
			part.save_as(path)
			mime = magic.Magic(mime=True).from_file(path)

			report += '  [y] uploaded file: \'%s\' (mime: %s) to file %s\n' % (part.filename, mime, path)
			submitted_file = model.SubmittedFile(evaluation=evaluation.id, mime=mime, path=path)

			session.add(submitted_file)

		evaluation.full_report = report
		session.add(evaluation)
		session.commit()
		session.close()

		req.context['result'] = {'result': 'correct'}

	def _evaluate_code(self, req, module, user_id, resp, data):
		evaluation = model.Evaluation(user=user_id, module=module.id)
		session.add(evaluation)
		session.commit()

		code = model.SubmittedCode(evaluation=evaluation.id, code=data)
		session.add(code)
		session.commit()

		if not module.autocorrect:
			session.commit()
			session.close()
			req.context['result'] = {'result': 'correct'}
			return

		result, report, output = util.programming.evaluate(module.task, module, user_id, data)

		points = module.max_points if result else 0
		evaluation.points = points
		evaluation.full_report = report

		session.commit()
		session.close()

		req.context['result'] = {'result': result, 'score': points, 'output': output}

	def on_post(self, req, resp, id):
		user = req.context['user']

		if not user.is_logged_in():
			resp.status = falcon.HTTP_400
			return

		module = session.query(model.Module).get(id)

		if module.type == ModuleType.GENERAL:
			self._upload_files(req, module, user.id, resp)
			return

		data = json.loads(req.stream.read())['content']

		if module.type == ModuleType.PROGRAMMING:
			self._evaluate_code(req, module, user.id, resp, data)
			# ToDo: Auto actions
			return

		if module.type == ModuleType.QUIZ:
			result, report = util.quiz.evaluate(module.task, module.id, data)
		elif module.type == ModuleType.SORTABLE:
			result, report = util.sortable.evaluate(module.task, module.id, data)
		elif module.type == ModuleType.TEXT:
			result, report = util.text.evaluate(module.task, module.id, data)


		points = module.max_points if result else 0
		evaluation = model.Evaluation(user=user.id, module=module.id, points=points, full_report=report)
		req.context['result'] = {'result': 'correct' if result else 'incorrect', 'score': points}

		if "action" in report:
			util.module.perform_action(module, user)

		session.add(evaluation)
		session.commit()
		session.close()

class ModuleSubmittedFile(object):
	
	def on_get(self, req, resp, id):

		user = req.context['user']

		if not user.is_logged_in():
			resp.status = falcon.HTTP_400
			return
		
		submittedFile = session.query(model.SubmittedFile).get(id)
		
		if submittedFile.evaluation.user.id == user.id or req.context['user'].role == 'admin' or req.context['user'].role == 'org':
			self.execute(submittedFile)
		else:
			resp.status = falcon.HTTP_400
			return
			
	def execute(self, submittedFile):
		path = submittedFile.path
		
		print path

		if not os.path.isfile(filePath):
			resp.status = falcon.HTTP_400
			return

		resp.content_type = magic.Magic(mime=True).from_file(path)
		resp.stream_len = os.path.getsize(path)
		resp.stream = open(path, 'rb')

class ModuleSubmittedFileDelete(ModuleSubmittedFile):
	
	def execute(self, submittedFile):
		
		try:
			os.remove(submittedFile.path)

			session.delete(submittedFile)
			session.commit()
			req.context['result'] = { 'status': 'ok' }
			
		except OSError:
			req.context['result'] = { 'status': 'error', 'error': 'Error removing file' }
			return
		except SQLAlchemyError:
			req.context['result'] = { 'status': 'error', 'error': 'Error removing file entry' }
			return