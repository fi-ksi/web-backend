import json, falcon

from db import session
import model
import auth

class Registration(object):

	def on_options(self, req, resp):
		return

	#TODO: Realne ukladani dat
	def on_post(self, req, resp):
		data = json.loads(req.stream.read())

		user = model.User(email=data['email'], password=auth.get_hashed_password(data['password']), first_name=data['first_name'], last_name=data['last_name'], sex='male', short_info=data["short_info"])
		session.add(user)
		session.commit()

		profile = model.Profile(user_id=user.id, addr_street=data['addr_street'], addr_city=data['addr_city'], addr_zip=data['addr_zip'], addr_country='cz',\
			school_name=data['school_name'], school_street=data['school_street'], school_city=data['school_city'], school_zip=data['school_zip'], school_country='cz', school_finish=int(data['school_finish']),\
			tshirt_size='S')
		session.add(profile)

		session.commit()
		session.close()

