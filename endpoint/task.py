import json

from db import session
import model

from util import PrerequisitiesEvaluator, decode_form_data
import endpoint.module

# FAKE DATA!!!!
fake_valuation = { 1 : True, 2 : False }

def _task_to_json(task):
	return {
		'id': task.id,
		'title': task.title,
		'author': task.author,
		'category': task.category,
		'intro': task.intro,
		'body': task.body,
		'max_score': task.max_score,
		'position': [ task.position_x, task.position_y ],
		'thread': task.thread,
		'time_published': task.time_published.isoformat(),
		'time_deadline': task.time_deadline.isoformat(),
		'node_parent': [ parent.parent_id for parent in task.parents ],
		'active': True if task.prerequisite_obj is None else PrerequisitiesEvaluator(fake_valuation, task.prerequisite_obj).evaluate(),
		'modules': [ module.id for module in task.modules ],
		'best_scores': [ 1 ],
		'my_score': 2,
		'solution': 'Prehledne vysvetlene reseni prikladu. Cely priklad spocival v blabla',
		'prerequisities': [],
		'submissions': [ ],
		'picture_active': 'img/nodes/vlna-1/node-big-travelling/base.svg',
		'picture_locked': 'img/nodes/vlna-1/node-big-travelling/base.svg',
		'picture_submitted': 'img/nodes/vlna-1/node-big-travelling/base.svg',
		'picture_finished': 'img/nodes/vlna-1/node-big-travelling/base.svg',
	}

class Task(object):

	def on_get(self, req, resp, id):
		task = session.query(model.Task).get(id)

		req.context['result'] = { 'task': _task_to_json(task) }


class Tasks(object):

	def on_get(self, req, resp):
		tasks = session.query(model.Task).all()

		req.context['result'] = { 'tasks': [ _task_to_json(task) for task in tasks ] }

class TaskSubmit(object):

	def on_post(self, req, resp, id):
		data = decode_form_data(req)
		points = {}
		report = ''

		for (key, val) in data.items():
			val = val[0]
			module_id = int(key.split('_')[1])
			solution = json.loads(val)['solution']

			module = session.query(model.Module).get(module_id)

			if module.type == 'quiz':
				result, eval_report = endpoint.module.quiz_evaluate(id, module_id, solution)
				report += eval_report
			elif module.type == 'sortable':
				result, eval_report = endpoint.module.sortable_evaluate(id, module_id, solution)
				report += eval_report

			points[int(module.id)] = module.points if result else 0
			report += '\n\n\n'

		report += '===========================\n'
		report += 'Points per module: ' + str(points) + '\n'
		report += '  => Overall points: ' + str(sum(points.values())) + '\n'

		print report
