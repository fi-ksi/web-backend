# -*- coding: utf-8 -*-
import json, falcon

from db import session
import model
import util

from thread import Thread
from util import config

class Post(object):

	def on_put(self, req, resp, id):
		self.on_get(req, resp, id)

	def on_get(self, req, resp, id):
		user_id = req.context['user'].get_id() if req.context['user'].is_logged_in() else None

		post = session.query(model.Post).get(id)

		if post is None:
			resp.status = falcon.HTTP_404
			return

		thread = session.query(model.Thread).get(post.thread)

		if thread is None:
			resp.status = falcon.HTTP_404
			return

		# Kontrola pristupu k prispevkum:
		# a) K prispevkum v eval vlakne mohou pristoupit jen orgove a jeden resitel
		# b) K ostatnim neverejnym prispevkum mohou pristoupit jen orgove.
		if not thread.public and ((not user.is_logged_in()) or (not user.is_org() or not util.thread.is_eval_thread(user.id, thread.id))):
			resp.status = falcon.HTTP_400
			return

		req.context['result'] = { 'post': util.post.to_json(post, user_id) }


class Posts(object):

	def on_post(self, req, resp):
		if not req.context['user'].is_logged_in():
			resp.status = falcon.HTTP_400
			return

		user = req.context['user']
		data = json.loads(req.stream.read())['post']

		thread_id = data['thread']
		thread = session.query(model.Thread).get(thread_id)

		if thread is None:
			resp.status = falcon.HTTP_400
			return

		task_thread = session.query(model.Task).filter(model.Task.thread == thread_id).first()
		solution_thread = session.query(model.SolutionComment).filter(model.SolutionComment.thread == thread_id, model.SolutionComment.user == user.id).first()

		# Podminky pristupu:
		#  1) Do vlakna ulohy neni mozne pristoupit, pokud je uloha pro uzivatele uzavrena.
		#  2) K vlaknu komentare nemohou pristoupit dalsi resitele.
		#  3) Do obecnych neverejnych vlaken muhou pristupovat orgove -- tato situace nastava pri POSTovani prnviho prispevku
		#     k opravovani, protoze vlakno opravovani jeste neni sprazeno s evaluation.
		if (task_thread and util.task.status(task_thread, user) == util.TaskStatus.LOCKED) or \
			(solution_thread and (solution_thread.user != user.id and not user.is_org())) or \
			(not thread.public and not solution_thread and not user.is_org()):
			resp.status = falcon.HTTP_400
			return

		user_class = session.query(model.User).get(user.id)

		#posilani mailu
		if user.role == 'participant' or user.role == 'participant_hidden':
			
			if task_thread:
				task_author = session.query(model.User).filter(model.User.id == task_thread.author).first()
				util.mail.send([ task_author.email ], u'[KSI-WEB] Nový příspěvek k úloze ' + task_thread.title, 
					u'<p>Ahoj,<br/>k tvé úloze <a href="' + config.ksi_web() + u'/ulohy/' + str(task_thread.id) + u'">' +\
					task_thread.title + u'</a> na <a href="'+ config.ksi_web() + '/">' + config.ksi_web() +u'</a> byl přidán nový komentář:</p><p><i>' +\
					user_class.first_name + u' ' + user_class.last_name + u':</i></p>' + data['body'] +\
					u'<p><a href="'  + config.ksi_web() + u'/ulohy/' + str(task_thread.id) + u'/diskuse">Přejít do diskuze.</a></p>' +\
					config.karlik_img(), True)
			elif solution_thread:
				correctors = [ r for r, in session.query(model.User.email).\
					join(model.Evaluation, model.Evaluation.evaluator == model.User.id).\
					join(model.Module, model.Evaluation.module == model.Module.id).\
					join(model.Task, model.Task.id == model.Module.task).\
					filter(model.Task.id == solution_thread.task).all() ]

				if correctors:
					task = session.query(model.Task).get(solution_thread.task)
					util.mail.send(correctors, u'[KSI-WEB] Nový komentář k tvé korektuře úlohy ' + task.title, \
						u'<p>Ahoj,<br/>k tvé korektuře úlohy <a href="' + config.ksi_web() + u'/ulohy/' + str(task.id) + u'">' + task.title +\
						u'</a> na <a href="'+ config.ksi_web() + '/">' + config.ksi_web() +u'</a> byl přidán nový komentář:<p><p><i>' +\
						user_class.first_name + ' ' + user_class.last_name + u':</i></p><p>' + data['body'] +\
						config.karlik_img(), True)
			else:
				util.mail.send([ config.ksi_conf() ], '[KSI-WEB] Nový příspěvek v obecné diskuzi',
					u'<p>Ahoj,<br/>do obecné diskuze na <a href="'+ config.ksi_web() + '/">' + config.ksi_web() +u'</a> byl přidán nový příspěvek:</p><p><i>' +\
					user_class.first_name + u' ' + user_class.last_name + u':</i></p>' + data['body'] +\
					u'<p><a href='  + config.ksi_web() + u'/forum/' + str(thread.id) + u'>Přejít do diskuze.</a></p>' +\
					config.karlik_img(), True)

		parent = data['parent']
		if parent and not session.query(model.Post).filter(model.Post.id == parent, model.Post.thread == thread_id).first():
			resp.status = falcon.HTTP_400
			return

		try:
			post = model.Post(thread=thread_id, author=user.id, body=data['body'], parent=parent)
			session.add(post)
			session.commit()
		except:
			session.rollback()
			raise

		req.context['result'] = { 'post': util.post.to_json(post, user.id) }

		session.close()
