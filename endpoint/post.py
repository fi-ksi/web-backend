# -*- coding: utf-8 -*-
import json, falcon

from db import session
import model
import util

from thread import Thread

#TODO change after testing
KSI_MAIL = 'smijakova.eva@gmail.com'
FORUM_URL = 'http://kyzikos.fi.muni.cz/forum/'

class Post(object):

	def on_put(self, req, resp, id):
		self.on_get(req, resp, id)

	def on_get(self, req, resp, id):
		user_id = req.context['user'].get_id() if req.context['user'].is_logged_in() else None

		post = session.query(model.Post).get(id)

		req.context['result'] = { 'post': util.post.to_json(post, user_id) }


class Posts(object):

	def on_post(self, req, resp):
		if not req.context['user'].is_logged_in():
			resp.status = falcon.HTTP_400
			return

		user = req.context['user']
		user_id = user.id
		data = json.loads(req.stream.read())['post']

		thread_id = data['thread']
		thread = session.query(model.Thread).get(thread_id)

		if thread is None:
			resp.status = falcon.HTTP_400
			return

		task_thread = session.query(model.Task).filter(model.Task.thread == thread_id).first()
		solution_thread = session.query(model.SolutionComment).filter(model.SolutionComment.thread == thread_id, model.SolutionComment.user == user_id).first()

		#po uzamceni 
		if task_thread and util.task.status(task_thread, user) == util.TaskStatus.LOCKED:
			resp.status = falcon.HTTP_400
			return
		#kdyz to neni public a ani solution, tak je to neco divnyho
		if not solution_thread and not thread.public:
			resp.status = falcon.HTTP_400
			return

		user_class = session.query(model.User).get(user.id)

		#posilani mailu
		#in progress 
		if user.role == 'participant':
			if task_thread:
				task_author = session.query(model.User).filter(model.User.id == task_thread.author)
				util.mail.send([ task_author.email ], 'Predmet', 'Obsah')
			elif solution_thread:
				pass
				'''
				correctors = session.query(model.User.email).\
					join(model.Evaluation, model.Evaluation.evaluator == model.User.id).\
					join(model.Module, model.Evaluation.module == model.Module.id).\
					join(model.Task, model.Task.id == model.Module.task).\
					filter(model.Task == solution_thread.task).all()
				util.mail.send(correctors, 'Predmet', 'Obsah')
				'''
			else:
				util.mail.send([ KSI_MAIL ], '[KSI-WEB] Nový příspěvek v obecné diskuzi', \
					u"Ahoj,<br/><br/>do obecné diskuze na https://ksi.fi.muni.cz byl přidán nový příspěvek:<br/><br/>" +\
					 u"<i>" + user_class.first_name + u' ' + user_class.last_name + u':</i><br/>' + data['body'] + u'<br/><br/>Přejít do diskuze:'  + FORUM_URL + str(thread.id) + u'<br/><br/>Web KSI') 

		parent = data['parent']
		if parent and not session.query(model.Post).filter(model.Post.id == parent, model.Post.thread == thread_id).first():
			resp.status = falcon.HTTP_400
			return

		post = model.Post(thread=thread_id, author=user_id, body=data['body'], parent=parent)

		session.add(post)
		session.commit()

		req.context['result'] = { 'post': util.post.to_json(post, user_id) }

		session.close()
