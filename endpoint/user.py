from db import session
import model


class User(object):
	def _schema(self, model_instances):
		inst = model_instances

		return {'user':
				{'id': inst.id, 'first_name': inst.name_first,
				 'last_name': inst.name_last}
				}

	def on_get(self, req, resp, id):
		#user = session.query(model.User).get(id)
		req.context['result'] = { 'user':  {"id": 1,
	  "first_name": "Katka",
	  "last_name": "Skvela",
	  "score": 150,
	  "tasks_num": 16,
	  "profile_picture": "http://placehold.it/50x50",
	  "achievements": [
		1,
		2,
		3
	  ]
	  } }


class Users(object):
	def _schema(self, model_instances):
		return {'users': [
			{'id': inst.id, 'first_name': inst.name_first,
			 'last_name': inst.name_last} for inst in model_instances
		]}

	def on_get(self, req, resp):
		#users = session.query(model.User).all()
		req.context['result'] = { "users": [
	{
	  "id": 1,
	  "first_name": "Katka",
	  "last_name": "Skvela",
	  "score": 150,
	  "tasks_num": 16,
	  "profile_picture": "http://placehold.it/50x50",
	  "achievements": [
		1,
		2,
		3
	  ]
	},
	{
	  "id": 2,
	  "first_name": "Katka",
	  "last_name": "Skvela",
	  "score": 150,
	  "tasks_num": 16,
	  "achievements": [
		2,
		3
	  ]
	},
	{
	  "id": 3,
	  "first_name": "Katka",
	  "last_name": "Skvela",
	  "score": 150,
	  "tasks_num": 16,
	  "achievements": [
		1,
		2,
		3
	  ]
	},
	{
	  "id": 4,
	  "first_name": "Katka",
	  "last_name": "Skvela",
	  "score": 150,
	  "tasks_num": 16,
	  "achievements": [
		2
	  ]
	},
	{
	  "id": 5,
	  "first_name": "Katka",
	  "last_name": "Skvela",
	  "score": 150,
	  "tasks_num": 16,
	  "achievements": [
		1,
		3
	  ]
	},
	{
	  "id": 6,
	  "first_name": "Jan",
	  "last_name": "Horacek",
	  "score": 1,
	  "tasks_num": 1,
	  "achievements": []
	}
  ]
}
