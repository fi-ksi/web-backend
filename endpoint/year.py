# -*- coding: utf-8 -*-

from db import session
import model
import util
import json

class Year(object):

	def on_get(self, req, resp, id):
		year = session.query(model.Year).get(id)

		if year is None:
			resp.status = falcon.HTTP_404
			return

		req.context['result'] = { 'year': util.year.to_json(year) }

	# UPDATE rocniku
	def on_put(self, req, resp, id):
		user = req.context['user']

		# Upravovat rocniky mohou jen ADMINI
		if (not user.is_logged_in()) or (not user.is_admin()):
			resp.status = falcon.HTTP_400
			return

		data = json.loads(req.stream.read())['year']

		year = session.query(model.Year).get(id)
		if year is None:
			resp.status = falcon.HTTP_404
			return

		year.id = data['index']
		year.year = data['year']
		year.sealed = data['sealed']
		year.point_pad = data['point_pad']

		try:
			session.commit()
		except:
			session.rollback()
			raise
		finally:
			session.close()

		self.on_get(req, resp, id)

	# Smazani rocniku
	def on_delete(self, req, resp, id):
		user = req.context['user']

		if (not user.is_logged_in()) or (not user.is_admin()):
			resp.status = falcon.HTTP_400
			return

		year = session.query(model.Year).get(id)
		if year is None:
			resp.status = falcon.HTTP_404
			return

		# Odstranit lze jen neprazdny rocnik
		waves_cnt = session.query(model.Wave).filter(model.Wave.year == year.id).count()
		if waves_cnt > 0:
			resp.status = falcon.HTTP_403
			return

		try:
			session.delete(year)
			session.commit()
			req.context['result'] = {}
		except:
			session.rollback()
			raise
		finally:
			session.close()

###############################################################################

class Years(object):

	def on_get(self, req, resp):
		years = session.query(model.Year).all()

		sum_points = util.task.max_points_year_dict()

		req.context['result'] = { 'years': [ util.year.to_json(year, sum_points[year.id]) for year in years ] }

	# Vytvoreni noveho rocniku
	def on_post(self, req, resp):
		user = req.context['user']

		# Vytvoret novy rocnik mohou jen ADMINI
		if (not user.is_logged_in()) or (not user.is_admin()):
			resp.status = falcon.HTTP_400
			return

		data = json.loads(req.stream.read())['year']

		year = model.Year(
			id = data['index'],
			year = data['year'],
			sealed = data['sealed'] if data['sealed'] else False,
			point_pad = data['point_pad']
		)

		try:
			session.add(year)
			session.commit()
		except:
			session.rollback()
			raise

		req.context['result'] = { 'year': util.year.to_json(year) }

		session.close()

