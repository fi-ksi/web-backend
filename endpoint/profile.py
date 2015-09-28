import json, falcon
from sqlalchemy import func

from db import session
import model
from achievement import achievements_ids
from task import max_points_dict

def _load_points_for_user(user_id):
	return session.query(model.Evaluation.module, func.max(model.Evaluation.points).label('points')).\
		join(model.Submission, model.Evaluation.submission == model.Submission.id).\
		filter(model.Submission.user == user_id).\
		group_by(model.Evaluation.module).all()

def _sum_points(user_id):
	return sum([ item.points for item in _load_points_for_user(user_id) ])

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

	def on_get(self, req, resp):
		user, profile = session.query(model.User).filter(model.User.id == 1).outerjoin(model.Profile, model.User.id == model.Profile.user_id).add_entity(model.Profile).first()

		points = _sum_points(user.id)
		successful = round((float(points)/sum(max_points_dict().values())) * 100)

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
			'score': points,
			'seasons': 1.5,
			'successful': int(successful),
			'results': [ 1, 2] } ] }
