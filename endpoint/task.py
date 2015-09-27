from db import session
import model

from util import PrerequisitiesEvaluator

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
		'modules': [ 0 ],
		'best_scores': [ 1 ],
		'my_score': 2,
		'solution': 'Prehledne vysvetlene reseni prikladu. Cely priklad spocival v blabla',
		'prerequisities': [] if len(task.parents) == 0 else { "id": 1, "parents": [ 1 ] },
		'submissions': [ ],
		'picture_active': 'img/nodes/vlna-1/node-uloha1.svg',
		'picture_locked': 'img/nodes/vlna-1/node-uloha2.svg',
		'picture_submitted': 'img/nodes/vlna-1/node-uloha2.svg',
		'picture_finished': 'img/nodes/vlna-1/node-uloha1.svg',
	}

class Task(object):

	def on_get(self, req, resp, id):
		task = session.query(model.Task).get(id)

		req.context['result'] = { 'task': _task_to_json(task) }


class Tasks(object):

	def on_get(self, req, resp):
		tasks = session.query(model.Task).filter(model.Task.id == 1).all()

		req.context['result'] = { 'tasks': [ _task_to_json(task) for task in tasks ] }
