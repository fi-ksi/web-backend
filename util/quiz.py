import json

from db import session
import model


def build(module_id):
	questions = _load_questions(module_id)

	return [ _question_to_json(question) for question in questions ]

def evaluate(task, module, data):
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

def _load_questions(module_id):
	return session.query(model.QuizQuestion).filter(model.QuizQuestion.module == module_id).order_by(model.QuizQuestion.order).all()

def _question_to_json(question):
	return {
		'type': question.type,
		'question': question.question,
		'text': question.text,
		'options': [ option.value for option in question.options ]
	}