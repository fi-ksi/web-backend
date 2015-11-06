import os, time, uuid, magic

import falcon

from db import session
import model
import util

class Content(object):

	def on_get(self, req, resp):

		filePath = 'data/content/' + req.get_param('path').replace('..', '');

		if not os.path.isfile(filePath):
			resp.status = falcon.HTTP_404
			return

		resp.content_type = magic.Magic(mime=True).from_file(filePath)
		resp.stream_len = os.path.getsize(filePath)
		resp.stream = open(filePath, 'rb')

class TaskContent(object):

	def on_get(self, req, resp, id, view):
		user = req.context['user']

		task = session.query(model.Task).get(id)

		if task is None or not user.is_logged_in():
			resp.status = falcon.HTTP_400
			return

		status = util.task.status(task, user)

		if view == 'zadani':
			if status == util.TaskStatus.LOCKED:
				resp.status = falcon.HTTP_400
				return
		else if view == 'reseni':
			if not solution_public(status, task, user):
				resp.status = falcon.HTTP_400
				return
		else:
			resp.status = falcon.HTTP_400
			return
		
		filePath = 'data/task-content/' + id + '/zadani/' + req.get_param('path').replace('..', '')

		if not os.path.isfile(filePath):
			resp.status = falcon.HTTP_404
			return

		resp.content_type = magic.Magic(mime=True).from_file(filePath)
		resp.stream_len = os.path.getsize(filePath)
		resp.stream = open(filePath, 'rb')
