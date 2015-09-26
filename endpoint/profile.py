import json, falcon

from db import session
import model
from achievement import achievements_ids

class Profile(object):
	def _schema(self, req):
		return {'profile': [
			{'id': 1, 'is_logged': bool(req.env['PERMISSIONS'])}
		]}

	def on_options(self, req, resp):
		resp.set_header('Access-Control-Allow-Credentials', 'true')
		resp.set_header('Access-Control-Allow-Headers', 'authorization')
		resp.set_header('Access-Control-Allow-Methods', 'GET,HEAD,PUT,PATCH,POST,DELETE')

		#resp.status = falcon.HTTP_204

	def on_get(self, req, resp):
		user, profile = session.query(model.User).filter(model.User.id == 1).outerjoin(model.Profile, model.User.id == model.Profile.user_id).add_entity(model.Profile).first()

		req.context['result'] = { 'profile': [ {
			'id': user.id,
			'signed_in': True,
			'first_name': user.first_name,
			'last_name': user.last_name,
			'profile_picture': '/img/avatar-default.svg',
			'short_info': profile.short_info,
			'email': user.email,
			'addr_street': profile.addr_street,
			'addr_city': profile.addr_city,
			'addr_zip': profile.addr_zip,
			'addr_country': profile.addr_country,
			'school_name': profile.school_name,
			'school_street': profile.school_street,
			'school_city': profile.school_city,
			'school_zip': profile.school_zip,
			'school_country': profile.school_country,
			'school_finish': profile.school_finish,
			'tshirt_size': profile.tshirt_size,
			'achievements': achievements_ids(user.achievements),
			'percentile': 69,
			'score': 42,
			'seasons': 1.5,
			'successful': 96,
			'results': [ 1, 2] } ] }
