from db import session
import model
import util
import falcon
import json

class Wave(object):

	def on_get(self, req, resp, id):
		user = req.context['user']
		wave = session.query(model.Wave).get(id)

		if wave is None:
			resp.status = falcon.HTTP_404
			return

		req.context['result'] = { 'wave': util.wave.to_json(wave) }

	# UPDATE vlny
	def on_put(self, req, resp, id):
		user = req.context['user']

		if (not user.is_logged_in()) or (not user.is_org()):
			resp.status = falcon.HTTP_400
			return

		data = json.loads(req.stream.read())['wave']

		try:
			wave = session.query(model.Wave).get(id)
			if wave is None:
				resp.status = falcon.HTTP_404
				return

			# Menit vlnu muze jen ADMIN nebo aktualni GARANT vlny.
			if not user.is_admin() and user.id != wave.garant:
				resp.status = falcon.HTTP_400
				return

			wave.index = data['index']
			wave.caption = data['caption']
			wave.time_published = data['time']
			wave.garant = data['garant']

			session.commit()
		except:
			session.rollback()
			raise
		finally:
			session.close()

		self.on_get(req, resp, id)

	# Smazani vlny
	def on_delete(self, req, resp, id):
		user = req.context['user']

		# Vlnu mohou smazat jen admini
		if (not user.is_logged_in()) or (not user.is_admin()):
			resp.status = falcon.HTTP_400
			return

		try:
			wave = session.query(model.Wave).get(id)
			if wave is None:
				resp.status = falcon.HTTP_404
				return

			# Smazat lze jen neprazdnou vlnu.
			tasks_cnt = session.query(model.Task).filter(model.Task.wave == wave.id).count()
			if tasks_cnt > 0:
				resp.status = falcon.HTTP_403
				return

			session.delete(wave)
			session.commit()
			req.context['result'] = {}
		except:
			session.rollback()
			raise
		finally:
			session.close()

###############################################################################

class Waves(object):

	def on_get(self, req, resp):
		user = req.context['user']
		waves = session.query(model.Wave).\
			filter(model.Wave.year == req.context['year']).all()

		req.context['result'] = { 'waves': [ util.wave.to_json(wave) for wave in waves ] }

	# Vytvoreni nove vlny
	def on_post(self, req, resp):
		user = req.context['user']
		year = req.context['year']

		# Vytvorit novou vlnu mohou jen admini.
		if (not user.is_logged_in()) or (not user.is_admin()):
			resp.status = falcon.HTTP_400
			return

		data = json.loads(req.stream.read())['wave']

		try:
			wave = model.Wave(
				year = year,
				index = data['index'],
				caption = data['caption'],
				garant = data['garant'],
				time_published = data['time_published']
			)

			session.add(wave)
			session.commit()
		except:
			session.rollback()
			raise
		finally:
			session.close()

		req.context['result'] = { 'wave': util.wave.to_json(wave) }

