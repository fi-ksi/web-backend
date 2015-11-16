from db import session
import model
import json
from sqlalchemy import desc
import falcon
import dateutil.parser

DEFAULT_IMAGE = 'img/box-ksi.svg'

def _artice_to_json(inst):
	return {
		'id': inst.id,
		'title': inst.title,
		'body': inst.body,
		'time_published': inst.time_created.isoformat(),
		'picture': inst.picture if inst.picture else DEFAULT_IMAGE,
		'published': inst.published
	}

class Article(object):

	# GET clanku
	def on_get(self, req, resp, id):
		data = session.query(model.Article).get(id)

		req.context['result'] = { 'article': _artice_to_json(data) }

	# aktualizace existujiciho clanku
	def on_put(self, req, resp, id):
		user = req.context['user']
		if (not user.is_logged_in()) or (not user.is_org()):
			resp.status = falcon.HTTP_400
			return

		data = json.loads(req.stream.read())['article']
		article = session.query(model.Article).get(id)
		if article is None:
			resp.status = falcon.HTTP_404
			return

		# TODO: article picture
		article.title = data['title']
		article.body = data['body']
		article.published = data['published']
		article.time_created = data['time_published']

		session.commit()
		session.close()

		self.on_get(req, resp, id)

	def on_delete(self, req, resp, id):
		user = req.context['user']
		if (not user.is_logged_in()) or (not user.is_org()):
			resp.status = falcon.HTTP_400
			return

		article = session.query(model.Article).get(id)
		if article is None:
			resp.status = falcon.HTTP_404
			return

		session.delete(article)
		session.commit()
		session.close()


class Articles(object):

	# Ziskani vsech clanku od \_start do \_limit
	def on_get(self, req, resp):
		user = req.context['user']

		query = session.query(model.Article).filter(model.Article.year == req.context['year'])
		if user is None or user.id is None or user.role == 'participant' or user.role == 'participant_hidden':
			query = query.filter(model.Article.published)
		query = query.order_by(desc(model.Article.time_created))

		limit = req.get_param_as_int('_limit')
		start = req.get_param_as_int('_start')
		count = query.count()

		data = query.all() if limit is None or start is None else query.slice(start, start + limit)

		articles = [ _artice_to_json(inst) for inst in data ]

		req.context['result'] = {'articles': articles, 'meta': { 'total': count } }

	# Pridani noveho clanku
	def on_post(self, req, resp):
		user = req.context['user']
		if (not user.is_logged_in()) or (not user.is_org()):
			resp.status = falcon.HTTP_400
			return

		data = json.loads(req.stream.read())['article']

		# TODO: article picture
		article = model.Article(
			author = user.id,
			title = data['title'],
			body = data['body'],
			published = data['published'],
			year = req.context['year'],
			time_created = dateutil.parser.parse(data['time_published'])
		)

		session.add(article)
		session.commit()

		req.context['result'] = { 'article': _artice_to_json(article) }

		session.close()

