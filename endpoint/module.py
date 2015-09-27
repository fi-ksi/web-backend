from db import session
import model

def _module_to_json(module):
	return { 'id': module.id, 'type': module.type, 'description': module.description }


class Module(object):

	def on_get(self, req, resp, id):
		module = session.query(model.Module).get(id)
		module_json = _module_to_json(module)

		if module.type == 'quiz':
			module_json['questions'] = self._build_quiz(module.id)
		elif module.type == 'programming':
			pass

		req.context['result'] = { 'module': module_json }

	def _quiz_question_to_json(self, question):
		return {
			'type': question.type,
			'question': question.question,
			'options': [ option.value for option in question.options ]
		}

	def _build_quiz(self, module_id):
		questions = session.query(model.QuizQuestion).filter(model.QuizQuestion.module == module_id).order_by(model.QuizQuestion.order).all()

		return [ self._quiz_question_to_json(question) for question in questions ]
