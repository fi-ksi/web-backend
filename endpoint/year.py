from db import session
import model
import util

class Year(object):

	def on_get(self, req, resp, id):
		year = session.query(model.Year).get(id)

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

		year.id = data['id']
		year.year = data['year']

		try:
			session.commit()
		except:
			session.rollback()
			raise
		finally:
			session.close()

		self.on_get(self, req, resp, id)

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

		try:
			session.delete(year)
			session.commit()
		except:
			session.rollback()
			raise
		finally:
			session.close()

###############################################################################

class Years(object):

	def on_get(self, req, resp):
		years = session.query(model.Year).all()

		req.context['result'] = { 'years': [ util.year.to_json(year) for year in years ] }

	# Vytvoreni noveho rocniku
	def on_post(self, req, resp):
		user = req.context['user']

		# Vytvoret novy rocnik mohou jen ADMINI
		if (not user.is_logged_in()) or (not user.is_admin()):
			resp.status = falcon.HTTP_400
			return

		data = json.loads(req.stream.read())['year']

		year = model.year(
			id = data['id'],
			year = data['year']
		)

		try:
			session.add(year)
			session.commit()
		except:
			session.rollback()
			raise
		finally:
			session.close()

		req.context['result'] = { 'year': util.year.to_json(year) }

