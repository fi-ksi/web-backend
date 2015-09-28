import json, falcon
from sqlalchemy import func

from db import session
import model
from achievement import achievements_ids
from task import max_points_dict
import multipart

def _load_points_for_user(user_id):
	return session.query(model.Evaluation.module, func.max(model.Evaluation.points).label('points')).\
		filter(model.Evaluation.user == user_id).\
		group_by(model.Evaluation.module).all()

def _sum_points(user_id):
	return sum([ item.points for item in _load_points_for_user(user_id) ])

def _profile_to_json(user, profile):
	points = _sum_points(user.id)
	successful = round((float(points)/sum(max_points_dict().values())) * 100)

	return { 'profile': [ {
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
			'score': points,
			'seasons': 1.5,
			'successful': int(successful),
			'results': [ 1, 2] } ] }

class Profile(object):
	def _schema(self, req):
		return {'profile': [
			{'id': 1, 'is_logged': bool(req.env['PERMISSIONS'])}
		]}

	def on_options(self, req, resp):
		pass
		#resp.set_header('Access-Control-Allow-Credentials', 'true')
		#resp.set_header('Access-Control-Allow-Headers', 'authorization')
		#resp.set_header('Access-Control-Allow-Methods', 'GET,HEAD,PUT,PATCH,POST,DELETE')

		#resp.status = falcon.HTTP_204

	def on_put(self, req, resp):
		data = json.loads(req.stream.read())
		user, profile = session.query(model.User).filter(model.User.id == 1).outerjoin(model.Profile, model.User.id == model.Profile.user_id).add_entity(model.Profile).first()

		user.first_name = data['first_name']
		user.last_name = data['last_name']
		user.email = data['email']

		profile.short_info = data['short_info']
		profile.addr_street = data['addr_street']
		profile.addr_city = data['addr_city']
		profile.addr_zip = data['addr_zip']
		profile.addr_country = data['addr_country']
		profile.school_name = data['school_name']
		profile.school_street = data['school_street']
		profile.school_city = data['school_city']
		profile.school_zip = data['school_zip']
		profile.school_country = data['school_country']
		profile.school_finish = data['school_finish']
		profile.tshirt_size = data['tshirt_size']

		session.add(user)
		session.add(profile)
		session.commit()

		req.context['result'] = _profile_to_json(user, profile)
		session.close()


	def on_get(self, req, resp):
		user, profile = session.query(model.User).filter(model.User.id == 1).outerjoin(model.Profile, model.User.id == model.Profile.user_id).add_entity(model.Profile).first()

		req.context['result'] = _profile_to_json(user, profile)

class PictureUploader(object):

	def on_post(self, req, resp):
		if not req.context['user'].is_logged_in():
			resp.status = falcon.HTTP_400
			return

		files = multipart.MultiDict()

		content_type, options = multipart.parse_options_header(req.content_type)
		boundary = options.get('boundary','')

		if not boundary:
			raise multipart.MultipartError("No boundary for multipart/form-data.")

		for part in multipart.MultipartParser(req.stream, boundary, req.content_length):
			files[part.name] = part

		file = files.get('file')

		if file.content_type != 'image/jpeg':
			print "unsupported type"
			resp.status = falcon.HTTP_400
			return

		user_id = req.context['user'].get_id()

		file.save_as('images/profile/user_%d.jpg' % user_id)
