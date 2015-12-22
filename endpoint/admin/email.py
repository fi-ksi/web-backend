import falcon
from sqlalchemy import func

from db import session
import model, util, json, sys

class Email(object):

	"""
	Specifikace POST pozadavku:
	{
		"Subject": String,
		"Body": String,
		"Sender": String,
		"Reply-To": String,
		"To": [] | [year_id_1, year_id_2, ...] (bud vsem resitelum, nebo resitelum v danych rocnicich),
		"Bcc": [String],
		"Gender": (both|male|female) - pokud neni vyplneno, je automaticky povazovano za "both",
		"KarlikSign": (true|false),
		"Easteregg": (true|false)
	}

	Backend edpovida:
	{
		count: Integer
	}
	"""
	def on_post(self, req, resp):
		user = req.context['user']

		if (not user.is_logged_in()) or (not user.is_org()):
			resp.status = falcon.HTTP_400
			return

		data = json.loads(req.stream.read())['e-mail']
		print data

		# Filtrovani uzivatelu
		if data['To'] != []:
			active = util.user.active_years_all()
			active = [ user for (user,year) in filter(lambda (user,year): (user.role == 'participant') and (year.id in data['To']), active) ]
			active = set(active)
			if ('Gender' in data) and (data['Gender'] != 'both'): active = filter(lambda user: user.sex == data['Gender'], active)
			to = [ user.email for user in active ]
		else:
			query = session.query(model.User).filter(model.User.role == 'participant')
			if ('Gender' in data) and (data['Gender'] != 'both'): query = query.filter(model.User.sex == data['Gender'])
			to = [ user.email for user in query.all() ]

		params = {
			'Return-Path': data['Sender'],
			'Errors-To': data['Sender'],
			'Reply-To': data['Reply-To'],
			'Sender': data['Sender']
		}

		body = data['Body']
		if ('KarlikSign' in data) and (data['KarlikSign']): body = body + util.config.karlik_img()
		if ('Easteregg' in data) and (data['Easteregg']): body = body + util.mail.easteregg()

		try:
			util.mail.send_multiple(to, data['Subject'], body, params, data['Bcc'])
			req.context['result'] = { 'count': len(to) }
		except Exception as e:
			req.context['result'] = { 'error': str(e) }
			resp.status = falcon.HTTP_500

