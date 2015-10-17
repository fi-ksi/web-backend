import json

from db import session
import model

def build(module_id):
	fixed, movable = _load_data(module_id)

	return { 'fixed': _type_to_json(fixed), 'movable': _type_to_json(movable) }

def evaluate(task, module, data):
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

def _load_data(module_id):
	fixed = session.query(model.Sortable).filter(model.Sortable.module == module_id, model.Sortable.type == 'fixed').order_by(model.Sortable.order).all()
	movable = session.query(model.Sortable).filter(model.Sortable.module == module_id, model.Sortable.type == 'movable').order_by(model.Sortable.order).all()

	return (fixed, movable)

def _type_to_json(type):
	return [ { 'content': row.content, 'style': row.style, 'offset': row.offset } for row in type ]