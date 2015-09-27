from db import session
import model

def _module_to_json(module):
	return { 'id': module.id, 'type': module.type, 'description': module.description }


class Module(object):

	def on_get(self, req, resp, id):
		module = session.query(model.Module).get(id)
		module_json = _module_to_json(module)

		if module.type == 'programming':
			code = self._build_programming(module.id)
			module_json['code'] = code
			module_json['default_code'] = code
		elif module.type == 'quiz':
			module_json['questions'] = self._build_quiz(module.id)
		elif module.type == 'sortable':
			module_json['sortable_list'] = self._build_sortable(module.id)

		req.context['result'] = { 'module': module_json }

	def _build_programming(self, module_id):
		programming = session.query(model.Programming).filter(model.Programming.module == module_id).first()

		return programming.default_code

	def _quiz_question_to_json(self, question):
		return {
			'type': question.type,
			'question': question.question,
			'options': [ option.value for option in question.options ]
		}

	def _build_quiz(self, module_id):
		questions = session.query(model.QuizQuestion).filter(model.QuizQuestion.module == module_id).order_by(model.QuizQuestion.order).all()

		return [ self._quiz_question_to_json(question) for question in questions ]

	def _sortable_type_to_json(self, sortable_type):
		return [ { 'content': row.content, 'style': row.style } for row in sortable_type ]

	def _build_sortable(self, module_id):
		fixed = session.query(model.Sortable).filter(model.Sortable.module == module_id, model.Sortable.type == 'fixed').order_by(model.Sortable.order).all()
		movable = session.query(model.Sortable).filter(model.Sortable.module == module_id, model.Sortable.type == 'movable').order_by(model.Sortable.order).all()

		return { 'fixed': self._sortable_type_to_json(fixed), 'movable': self._sortable_type_to_json(movable) }
