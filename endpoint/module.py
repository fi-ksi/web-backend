import json

from db import session
import model

def _module_to_json(module):
	return { 'id': module.id, 'type': module.type, 'description': module.description }

def _load_questions(module_id):
	return session.query(model.QuizQuestion).filter(model.QuizQuestion.module == module_id).order_by(model.QuizQuestion.order).all()

def _load_sortable(module_id):
	fixed = session.query(model.Sortable).filter(model.Sortable.module == module_id, model.Sortable.type == 'fixed').order_by(model.Sortable.order).all()
	movable = session.query(model.Sortable).filter(model.Sortable.module == module_id, model.Sortable.type == 'movable').order_by(model.Sortable.order).all()

	return (fixed, movable)

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
		questions = _load_questions(module_id)

		return [ self._quiz_question_to_json(question) for question in questions ]

	def _sortable_type_to_json(self, sortable_type):
		return [ { 'content': row.content, 'style': row.style } for row in sortable_type ]

	def _build_sortable(self, module_id):
		fixed, movable = _load_sortable(module_id)

		return { 'fixed': self._sortable_type_to_json(fixed), 'movable': self._sortable_type_to_json(movable) }

def quiz_evaluate(task, module, data):
	report = '=== Evaluating quiz id \'%s\' for task id \'%s\' ===\n\n' % (module, task)
	report += ' Raw data: ' + json.dumps(data) + '\n'
	report += ' Evaluation:\n'

	overall_results = True
	questions = _load_questions(module)
	i = 0

	for question in questions:
		answers_user = [ int(item) for item in data[i] ]
		answers_correct = []

		j = 0
		for option in question.options:
			if option.is_correct:
				answers_correct.append(j)
			j += 1

		is_correct = (answers_user == answers_correct)

		report += '  [%s] Question %d (id: %d) -- user answers: %s, correct answers: %s\n' % ('y' if is_correct else 'n', i, question.id, answers_user, answers_correct)
		overall_results &= is_correct
		i += 1

	report += '\n Overall result: [' + ('y' if overall_results else 'n') + ']'

	return (overall_results, report)

def sortable_evaluate(task, module, data):
	report = '=== Evaluating sortable id \'%s\' for task id \'%s\' ===\n\n' % (module, task)
	report += ' Raw data: ' + json.dumps(data) + '\n'
	report += ' Evaluation:\n'

	sortable = session.query(model.Sortable).filter(model.Sortable.module == module).order_by(model.Sortable.order).all()
	correct_order = {}
	user_order = { i: data[i].encode('utf-8') for i in range(len(data)) }

	i = 0
	j = 0
	for item in sortable:
		if item.type == 'fixed':
			value = 'a' + str(i)
			i += 1
		else:
			value = 'b' + str(j)
			j += 1

		correct_order[item.correct_position - 1] = value

	result = (correct_order == user_order)

	report += '  User order: %s\n' % user_order
	report += '  Correct order: %s\n' % correct_order
	report += '\n Overall result: [%s]' % ('y' if result else 'n')

	return (result, report)
