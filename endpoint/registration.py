import json, falcon

from db import session
import model
import auth
import util

class Registration(object):

	def on_options(self, req, resp):
		return

	def on_post(self, req, resp):
		data = json.loads(req.stream.read())

		existing_user = session.query(model.User).filter(model.User.email == data['email']).first()
		if existing_user != None:
			req.context['result'] = { 'error': "duplicate_user" }
			return

		user = model.User(email=data['email'], password=auth.get_hashed_password(data['password']), first_name=data['first_name'], last_name=data['last_name'], sex=data['gender'], short_info=data["short_info"])
		session.add(user)
		session.commit()

		profile = model.Profile(user_id=user.id, addr_street=data['addr_street'], addr_city=data['addr_city'], addr_zip=data['addr_zip'], addr_country=data['addr_country'],\
			school_name=data['school_name'], school_street=data['school_street'], school_city=data['school_city'], school_zip=data['school_zip'], school_country=data['school_country'], school_finish=int(data['school_finish']),\
			tshirt_size=data['tshirt_size'].upper())
		session.add(profile)

		session.commit()

		util.mail.send(user.email, 'Registrace do KSI', 'Ahoj ahoj,\nvitame Te v KSI a mame Te radi...\n\nOrgove')
		session.close()

