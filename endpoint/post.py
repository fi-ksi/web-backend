# -*- coding: utf-8 -*-
import json, falcon

from db import session
import model
import util

from thread import Thread

KSI_MAIL = session.query(model.Config).get("ksi_conf").value
FORUM_URL = session.query(model.Config).get("web_url").value + 'forum/'
TASK_FORUM_URL = session.query(model.Config).get("web_url").value + 'ulohy/'
KARLIK_IMG = session.query(model.Config).get("mail_sign").value

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
		if user.role == 'participant':
			
			if task_thread:	
				task_author = session.query(model.User).filter(model.User.id == task_thread.author).first()
				util.mail.send([ task_author.email ], '[KSI-WEB] Nový příspěvek k tvé úloze', 
					u'<p>Ahoj,<br/>k tvé úloze '  + task_thread.title + u' na https://ksi.fi.muni.cz byl přidán nový komentář:</p><p>' +\
					 user_class.first_name + u' ' + user_class.last_name + u':</p><p>' + data['body'] +\
					 '</p><p><a href='  + TASK_FORUM_URL + str(thread.id) + u'/diskuse >Přejít do diskuze.</a>' +\
					 u'<hr/>' + KARLIK_IMG, True)
			elif solution_thread:
				#TODO
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
				util.mail.send([ KSI_MAIL ], '[KSI-WEB] Nový příspěvek v obecné diskuzi', 
					u'<p>Ahoj,<br/>do obecné diskuze na https://ksi.fi.muni.cz byl přidán nový příspěvek:</p><p>' +\
					 user_class.first_name + u' ' + user_class.last_name + u':</p><p>' + data['body'] +\
					 u'</p><p><a href='  + FORUM_URL + str(thread.id) + u'>Přejít do diskuze.</a>' +\
					 u'<hr/>' + KARLIK_IMG, True)

		parent = data['parent']
		if parent and not session.query(model.Post).filter(model.Post.id == parent, model.Post.thread == thread_id).first():
			resp.status = falcon.HTTP_400
			return

		post = model.Post(thread=thread_id, author=user_id, body=data['body'], parent=parent)

		session.add(post)
		session.commit()

		req.context['result'] = { 'post': util.post.to_json(post, user_id) }

		session.close()
