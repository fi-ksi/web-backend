# -*- coding: utf-8 -*-

import json, falcon

from db import session
import model
import util
import sys
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
import traceback

from thread import Thread
from util import config

class Post(object):

	# Uprava prispevku
	def on_put(self, req, resp, id):
		try:
			user = req.context['user']

			if (not user.is_logged_in()) or (not user.is_org()):
				# Toto tady musi byt -- jinak nefunguje frontend.
				self.on_get(req, resp, id)
				return

			data = json.loads(req.stream.read())['post']

			post = session.query(model.Post).get(id)
			if post is None:
				resp.status = falcon.HTTP_404
				return

			post.author = data['author']
			post.body = data['body']

			session.commit()
		except SQLAlchemyError:
			session.rollback()
			raise
		finally:
			session.close()

		self.on_get(req, resp, id)

	def on_get(self, req, resp, id):
		try:
			user = req.context['user']
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
			if not thread.public and ((not user.is_logged_in()) or (not user.is_org() and not util.thread.is_eval_thread(user.id, thread.id))):
				resp.status = falcon.HTTP_400
				return

			req.context['result'] = { 'post': util.post.to_json(post, user_id) }
		except SQLAlchemyError:
			session.rollback()
			raise
		finally:
			session.close()

	def on_delete(self, req, resp, id):
		try:
			user = req.context['user']

			if (not user.is_logged_in()) or (not user.is_org()):
				resp.status = falcon.HTTP_400
				return

			post = session.query(model.Post).get(id)
			if post is None:
				resp.status = falcon.HTTP_404
				return

			session.delete(post)
			session.commit()
			req.context['result'] = {}
		except SQLAlchemyError:
			session.rollback()
			raise
		finally:
			session.close()


class Posts(object):

	def on_post(self, req, resp):
		try:
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

			if req.context['year_obj'].sealed:
				resp.status = falcon.HTTP_403
				req.context['result'] = { 'errors': [ { 'status': '403', 'title': 'Forbidden', 'detail': u'Ročník zapečetěn.' } ] }
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

			# Kontrola existence rodicovskeho vlakna
			parent = session.query(model.Post).filter(model.Post.id == data['parent'], model.Post.thread == thread_id).first()
			if data['parent'] and not parent:
				resp.status = falcon.HTTP_400
				return

			# Aktualizace navstivenosti vlakna
			visit = util.thread.get_visit(user.id, thread_id)
			if visit:
				visit.last_last_visit = visit.last_visit
				visit.last_visit = text('CURRENT_TIMESTAMP + INTERVAL 1 SECOND')
			else:
				time = text('CURRENT_TIMESTAMP + INTERVAL 1 SECOND')
				visit = model.ThreadVisit(thread=thread_id, user=user.id, last_visit=time, last_last_visit=time)
				session.add(visit)
			session.commit()

			# Tady si pamatujeme, komu jsme email jiz odeslali
			sent_emails = set()

			# ------------------------------------------
			# Odesilani emailu orgum
			if user.role == 'participant' or user.role == 'participant_hidden':

				if task_thread:
					# Vlakno k uloze -> posilame email autoru ulohy, spoluautoru ulohy a garantovi vlny
					task_author_email = session.query(model.User.email).filter(model.User.id == task_thread.author).scalar()
					wave_garant_email = session.query(model.User.email).\
						join(model.Wave, model.Wave.garant == model.User.id).\
						join(model.Task, model.Task.wave == model.Wave.id).\
						filter(model.Task.id == task_thread.id).scalar()
					sent_emails.add(task_author_email)
					sent_emails.add(wave_garant_email)
					if task_thread.co_author:
						task_co_author_email = session.query(model.User.email).filter(model.User.id == task_thread.co_author).scalar()
						sent_emails.add(task_co_author_email)
					try:
						util.mail.send([task_author_email, task_co_author_email], u'[KSI-WEB] Nový příspěvek k úloze ' + task_thread.title,
							u'<p>Ahoj,<br/>k tvé úloze <a href="' + config.ksi_web() + u'/ulohy/' + str(task_thread.id) + u'">' +\
							task_thread.title + u'</a> na <a href="'+ config.ksi_web() + '/">' + config.ksi_web() +u'</a> byl přidán nový komentář:</p><p><i>' +\
							user_class.first_name + u' ' + user_class.last_name + u':</i></p>' + data['body'] +\
							u'<p><a href="'  + config.ksi_web() + u'/ulohy/' + str(task_thread.id) + u'/diskuse">Přejít do diskuze.</a></p>' +\
							config.karlik_img() + util.mail.easteregg(), cc=wave_garant_email)
					except:
						exc_type, exc_value, exc_traceback = sys.exc_info()
						traceback.print_exception(exc_type, exc_value, exc_traceback, file=sys.stderr)

				elif solution_thread:
					# Vlakno k oprave -> posilame email autoru opravy
					correctors = [ r for r, in session.query(model.User.email).\
						join(model.Evaluation, model.Evaluation.evaluator == model.User.id).\
						join(model.Module, model.Evaluation.module == model.Module.id).\
						join(model.Task, model.Task.id == model.Module.task).\
						filter(model.Task.id == solution_thread.task).all() ]

					for corr_email in correctors: sent_emails.add(corr_email)

					if correctors:
						task = session.query(model.Task).get(solution_thread.task)
						try:
							util.mail.send(correctors, u'[KSI-WEB] Nový komentář k tvé korektuře úlohy ' + task.title, \
								u'<p>Ahoj,<br/>k tvé <a href="'+ config.ksi_web() + u'/admin/opravovani?task_='+str(task.id)+u'&participant_='+str(user_class.id)+\
								u'">korektuře</a> úlohy <a href="' + config.ksi_web() + u'/ulohy/' + str(task.id) + u'">' + task.title +\
								u'</a> na <a href="'+ config.ksi_web() + '/">' + config.ksi_web() +u'</a> byl přidán nový komentář:<p><p><i>' +\
								user_class.first_name + ' ' + user_class.last_name + u':</i></p><p>' + data['body'] +\
								config.karlik_img() + util.mail.easteregg())
						except:
							exc_type, exc_value, exc_traceback = sys.exc_info()
							traceback.print_exception(exc_type, exc_value, exc_traceback, file=sys.stderr)
				else:
					# Obecna diskuze -> email na ksi@fi.muni.cz
					try:
						sent_emails.add(config.ksi_conf())
						util.mail.send(config.ksi_conf(), '[KSI-WEB] Nový příspěvek v obecné diskuzi',
							u'<p>Ahoj,<br/>do obecné diskuze na <a href="'+ config.ksi_web() + '/">' + config.ksi_web() +u'</a> byl přidán nový příspěvek:</p><p><i>' +\
							user_class.first_name + u' ' + user_class.last_name + u':</i></p>' + data['body'] +\
							u'<p><a href='  + config.ksi_web() + u'/forum/' + str(thread.id) + u'>Přejít do diskuze.</a></p>' +\
							config.karlik_img() + util.mail.easteregg())
					except:
						exc_type, exc_value, exc_traceback = sys.exc_info()
						traceback.print_exception(exc_type, exc_value, exc_traceback, file=sys.stderr)

			# ------------------------------------------
			# Pridani prispevku
			post = model.Post(thread=thread_id, author=user.id, body=data['body'], parent=data['parent'])
			session.add(post)
			session.commit()

			# ------------------------------------------
			# Odesilani emailu v reakci na muj prispevek:

			if parent:
				parent_user = session.query(model.User).get(parent.author)
				parent_profile = session.query(model.Profile).get(parent.author)
				if (parent_user.email not in sent_emails) and (parent_profile.notify_response):
					try:
						sent_emails.add(parent_user.email)

						body = u"<p>Ahoj,<br>do diskuze <a href=\"%s\">%s</a> byl přidán nový příspěvek.</p>" % (util.config.ksi_web() + "/forum/" + str(thread.id), thread.title)
						body += util.post.to_html(parent, parent_user)
						body += u"<div style='margin-left: 50px;'>%s</div>" % (util.post.to_html(post))
						body += util.config.karlik_img()
						body += u"<hr><p style='font-size: 70%%;'>Tuto zprávu dostáváš, protože máš v nastavení na <a href=\"%s\">KSI webu</a> aktivované zasílání notifikací. Pokud nechceš dostávat notifikace, změň si nastavení na webu.</p>" % (util.config.ksi_web())


						util.mail.send(parent_user.email, u'[KSI-WEB] Nový příspěvek v diskuzi %s' % (thread.title), body)
					except:
						exc_type, exc_value, exc_traceback = sys.exc_info()
						traceback.print_exception(exc_type, exc_value, exc_traceback, file=sys.stderr)

			req.context['result'] = { 'post': util.post.to_json(post, user.id) }
		except SQLAlchemyError:
			session.rollback()
			raise
		finally:
			session.close()

