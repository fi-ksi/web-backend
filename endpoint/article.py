from db import session
import model
import json
from sqlalchemy import desc

DEFAULT_IMAGE = 'img/box-ksi.svg'

def _artice_to_json(inst):
	return { 'id': inst.id, 'title': inst.title, 'body': inst.body, 'time_published': inst.time_created.isoformat(), 'picture': inst.picture if inst.picture else DEFAULT_IMAGE }

class Article(object):

	def on_get(self, req, resp, id):
		data = session.query(model.Article).get(id)

		req.context['result'] = { 'article': _artice_to_json(data) }


class Articles(object):

	def on_get(self, req, resp):
		user = req.context['user']

		if user is None or user.role === 'participant':
			query = session.query(model.Article).filter(model.Article.published).order_by(desc(model.Article.time_created))
		else
			query = session.query(model.Article).order_by(desc(model.Article.time_created))

		limit = req.get_param_as_int('_limit')
		start = req.get_param_as_int('_start')
		count = query.count()

		data = query.all() if limit is None or start is None else query.slice(start, start + limit)

		articles = [ _artice_to_json(inst) for inst in data ]

		req.context['result'] = {'articles': articles, 'meta': { 'total': count } }

