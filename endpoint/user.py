from db import session
import model

def _user_to_json(user):
	return { 'id': user.id, 'first_name': user.first_name, 'last_name': user.last_name,
			'score': 150, 'tasks_num': 16, 'profile_picture': 'http://placehold.it/50x50',
			'achievements': [ 1, 2, 3 ] }


class User(object):

	def on_get(self, req, resp, id):
		user = session.query(model.User).get(id)

		req.context['result'] = { 'user': _user_to_json(user) }



class Users(object):
	def on_get(self, req, resp):
		users = session.query(model.User).all()


		req.context['result'] = { "users": [ _user_to_json(user) for user in users ] }
