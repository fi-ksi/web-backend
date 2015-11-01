import json, falcon, os, magic, multipart
from sqlalchemy import func

import datetime
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
		count = session.query(model.Evaluation.points).filter(model.Evaluation.user == user.id, model.Evaluation.module == id).\
			join(model.Module, model.Module.id == model.Evaluation.module).\
			join(model.Task, model.Task.id == model.Module.task).\
			filter(model.Task.evaluation_public).count()

		if count > 0:
			status = session.query(func.max(model.Evaluation.points).label('points')).\
				filter(model.Evaluation.user == user.id, model.Evaluation.module == id).\
				join(model.Module, model.Module.id == model.Evaluation.module).\
				join(model.Task, model.Task.id == model.Module.task).\
				filter(model.Task.evaluation_public).first()
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
		# Pokud uz existuji odevzdane soubory, nevytvarime nove
		# evaluation, pouze pripojujeme k jiz existujicimu
		existing = util.module.existing_evaluation(module.id, user_id)
		if len(existing) > 0:
			evaluation = session.query(model.Evaluation).get(existing[0])
			evaluation.time = datetime.datetime.now()
			report = evaluation.full_report
		else:
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
			path = '%s/%s' % (dir, part.filename)
			part.save_as(path)
			mime = magic.Magic(mime=True).from_file(path)

			report += '  [y] uploaded file: \'%s\' (mime: %s) to file %s\n' % (part.filename, mime, path)

			# Pokud je tento soubor jiz v databazi, zaznam znovu nepridavame
			file_in_db = session.query(model.SubmittedFile).\
				filter(model.SubmittedFile.evaluation == evaluation.id).\
				filter(model.SubmittedFile.path == path).scalar()

			if file_in_db is None:
				submitted_file = model.SubmittedFile(evaluation=evaluation.id, mime=mime, path=path)
				session.add(submitted_file)

		evaluation.full_report = report
		session.add(evaluation)
		session.commit()
		session.close()

		req.context['result'] = {'result': 'correct'}

	def _evaluate_code(self, req, module, user_id, resp, data):
		# Pokud neni modul autocorrrect, pridavame submitted_files
		# k jednomu evaluation.
		# Pokud je autocorrect, pridavame evaluation pro kazde vyhodnoceni souboru.
		existing = util.module.existing_evaluation(module.id, user_id)
		if (not module.autocorrect) and (len(existing) > 0):
			evaluation = session.query(model.Evaluation).get(existing[0])
			evaluation.time = datetime.datetime.now()
		else:
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

		points = module.max_points if result == 'correct' else 0
		evaluation.points = points
		evaluation.full_report += report

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
            execute(submittedFile)
        else:
            resp.status = falcon.HTTP_400
			return
            
    def execute(self, submittedFile):
        path = submittedFile.path
        if not os.path.isfile(filePath):
            resp.status = falcon.HTTP_400
            return

        resp.content_type = magic.Magic(mime=True).from_file(path)
        resp.stream_len = os.path.getsize(path)
        resp.stream = open(path, 'rb')

class ModuleSubmittedFileDelete(ModuleSubmittedFile):
    
    def execute(self, submittedFile):
        
        try:
            if submittedFile.evaluation.user.id == user.id or req.context['user'].role == 'admin' or req.context['user'].role == 'org':

                os.remove(submittedFile.path)

                session.delete(submittedFile)
                session.commit()
                req.context['result'] = { 'status': 'ok' }
            else:
                resp.status = falcon.HTTP_400
                return
        except OSError:
            req.context['result'] = { 'status': 'error', 'error': 'Error removing file' }
            return
        except SQLAlchemyError:
            req.context['result'] = { 'status': 'error', 'error': 'Error removing file entry' }
            return