import json

from db import session
import model
import json

"""
Specifikace \data v databazi modulu pro "quiz":
	"quiz": [{
		"type": Enum('checkbox', 'radio')
		"question": Text
		"text": String
		"options": ["opt1", "opt2", ...]
		"correct": [seznam_indexu_spravnych_odpovedi]
	},
	{
		...
	}]
"""

def to_json(db_dict, user_id):
	return [ _question_to_json(question) for question in db_dict['quiz'] ]

def evaluate(task, module, data):
	report = '=== Evaluating quiz id \'%s\' for task id \'%s\' ===\n\n' % (module.id, task)
	report += ' Raw data: ' + json.dumps(data) + '\n'
	report += ' Evaluation:\n'

	overall_results = True
	questions = json.loads(module.data)['quiz']
	i = 0

	for question in questions:
		answers_user = [ int(item) for item in data[i] ]
		is_correct = (answers_user == question['correct'])

		report += '  [%s] Question %d -- user answers: %s, correct answers: %s\n' % ('y' if is_correct else 'n', i, answers_user, question['correct'])
		overall_results &= is_correct
		i += 1

	report += '\n Overall result: [' + ('y' if overall_results else 'n') + ']'

	return (overall_results, report)

def _question_to_json(question):
	return {
		'type': question['type'],
		'question': question['question'],
		'text': question['text'],
		'options': question['options']
	}
