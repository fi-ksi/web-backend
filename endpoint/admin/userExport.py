# -*- coding: utf-8 -*-

import falcon
from db import session
import model, util, os
from StringIO import StringIO
from sqlalchemy import func, distinct, desc, text, or_

class UserExport(object):

	# Vraci csv vsech resitelu vybraneho rocniku.
	def on_get(self, req, resp):
		user = req.context['user']

		if (not user.is_logged_in()) or (not user.is_org()):
			resp.status = falcon.HTTP_400
			return

		inMemoryOutputFile = StringIO()

		# Tady se dela spoustu magie kvuli tomu, aby se usetrily SQL dotazy
		# Snazime se minimalizovat pocet dotazu, ktere musi byt provedeny pro kadeho uzivatele
		# a misto toho provest pouze jeden MEGA dotaz.

		# Skore uzivatele per modul (zahrnuje jen moduly evaluation_public)
		per_user = session.query(model.Evaluation.user.label('user'), func.max(model.Evaluation.points).label('points')).\
			join(model.Module, model.Evaluation.module == model.Module.id).\
			join(model.Task, model.Task.id == model.Module.task).\
			filter(model.Task.evaluation_public).\
			join(model.Wave, model.Wave.id == model.Task.wave).\
			filter(model.Wave.year == req.context['year']).\
			group_by(model.Evaluation.user, model.Evaluation.module).subquery()

		# Pocet odevzdanych uloh (zahrnuje i module not evaluation_public i napriklad automaticky opravovane moduly s 0 body)
		tasks_per_user = session.query(model.Evaluation.user.label('user'), func.count(distinct(model.Task.id)).label('tasks_cnt')).\
			join(model.Module, model.Evaluation.module == model.Module.id).\
			join(model.Task, model.Task.id == model.Module.task).\
			join(model.Wave, model.Wave.id == model.Task.wave).\
			filter(model.Wave.year == req.context['year']).\
			group_by(model.Evaluation.user).subquery()

		# Ziskame vsechny uzivatele
		# Tem, kteri maji evaluations, je prirazen pocet bodu a pocet odevzdanych uloh
		# Vraci n tici: (model.User, total_score, tasks_cnt, model.Profile)
		users = session.query(model.User, model.Profile, func.sum(per_user.c.points).label("total_score"), tasks_per_user.c.tasks_cnt.label('tasks_cnt')).\
			join(per_user, model.User.id == per_user.c.user).\
			join(tasks_per_user, model.User.id == tasks_per_user.c.user).\
			join(model.Profile, model.User.id == model.Profile.user_id).\
			filter(model.User.role == 'participant').\
			filter(text("tasks_cnt"), text("tasks_cnt") > 0).\
			group_by(model.User).order_by(desc("total_score"), model.User.last_name, model.User.first_name).all()

		sum_points = util.task.sum_points(req.context['year'], bonus=False)
		sum_points_bonus = util.task.sum_points(req.context['year'], bonus=True)
		inMemoryOutputFile.write(u"Celkem bodů: " + str(sum_points) + u", včetně bonusových úloh: " + str(sum_points_bonus) + '\n')
		inMemoryOutputFile.write(\
			u"Pořadí;" +\
			u"Příjmení;" +\
			u"Jméno;" +\
			u"Body;"+\
			u"Úspěšný řešitel;"+\
			u"E-mail;" +\
			u"Ulice;" +\
			u"Město;" +\
			u"PSČ;" +\
			u"Země;" +\
			u"Škola;" +\
			u"Adresa školy;" +\
			u"Město školy;" +\
			u"PSČ školy;" +\
			u"Země školy;" +\
			u'Rok maturity\n'\
		)

		order = 0
		last_points = -1
		for i in range(0, len(users)):
			user      = users[i][0]
			profile   = users[i][1]
			points    = users[i][2]
			tasks_cnt = users[i][3]
			if points != last_points:
				order = i+1
				last_points = points

			inMemoryOutputFile.write(\
				str(order)+";"+\
				user.last_name+";" +\
				user.first_name+";" +\
				str(points)+";"+\
				('A' if points >= 0.6*sum_points else 'N')+";"+\
				user.email+";" +\
				profile.addr_street+";" +\
				profile.addr_city+";" +\
				profile.addr_zip+";" +\
				profile.addr_country+";" +\
				profile.school_name+";" +\
				profile.school_street+";" +\
				profile.school_city+";" +\
				profile.school_zip+";" +\
				profile.school_country+";" +\
				str(profile.school_finish)+'\n'\
			)

		resp.set_header('Content-Disposition', "inline; filename=\"resitele_" + str(req.context['year']) + ".csv\"")
		resp.content_type = "text/csv"
		resp.stream_len = inMemoryOutputFile.len
		resp.body = inMemoryOutputFile.getvalue()

		inMemoryOutputFile.close()

