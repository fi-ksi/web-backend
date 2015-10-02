from db import session
import model
import util

def points_per_task(user_id):
	tasks = session.query(model.Task)

	return { task.id: util.task.points(task.id, user_id) for task in tasks }
