# -*- coding: utf-8 -*-

from db import session
import model
import json
from sqlalchemy import desc
import falcon
import dateutil.parser
import util

DEFAULT_IMAGE = 'img/box-ksi.svg'

def _artice_to_json(inst):
	return {
		'id': inst.id,
		'title': inst.title,
		'body': inst.body,
		'time_published': inst.time_created.isoformat(),
		'picture': inst.picture if inst.picture else DEFAULT_IMAGE,
		'published': inst.published,
		'author': inst.author,
		'content': inst.resource
	}

class Article(object):

	# GET clanku
	def on_get(self, req, resp, id):
		user = req.context['user']

		data = session.query(model.Article).get(id)

		if data is None:
			req.context['result'] = { 'errors': [ { 'status': '404', 'title': 'Not Found', 'detail': u'Článek s tímto ID neexistuje.' } ] }
			resp.status = falcon.HTTP_404
			return

		req.context['result'] = {
			'article': _artice_to_json(data),
			'contents': [ util.content.dir_to_json(data.resource) ] if data.resource and user.is_org() else []
		}

	# aktualizace existujiciho clanku
	def on_put(self, req, resp, id):
		user = req.context['user']
		if (not user.is_logged_in()) or (not user.is_org()):
			req.context['result'] = { 'errors': [ { 'status': '401', 'title': 'Unauthorized', 'detail': u'Upravit článek může pouze organizátor.' } ] }
			resp.status = falcon.HTTP_400
			return

		data = json.loads(req.stream.read())['article']

		try:
			article = session.query(model.Article).get(id)
			if article is None:
				req.context['result'] = { 'errors': [ { 'status': '404', 'title': 'Not Found', 'detail': u'Článek s tímto ID neexistuje.' } ] }
				resp.status = falcon.HTTP_404
				return

			article.title = data['title']
			article.body = data['body']
			article.published = data['published']
			article.time_created = data['time_published']
			article.resource = data['resource']
			article.picture = data['picture']

			session.commit()
		except:
			session.rollback()
			raise
		finally:
			session.close()

		self.on_get(req, resp, id)

	# Smazani clanku
	def on_delete(self, req, resp, id):
		user = req.context['user']
		if (not user.is_logged_in()) or (not user.is_org()):
			req.context['result'] = { 'errors': [ { 'status': '401', 'title': 'Unauthorized', 'detail': u'Smazat článek může pouze organizátor.' } ] }
			resp.status = falcon.HTTP_400
			return

		try:
			article = session.query(model.Article).get(id)
			if article is None:
				req.context['result'] = { 'errors': [ { 'status': '404', 'title': 'Not Found', 'detail': u'Článek s tímto ID neexistuje.' } ] }
				resp.status = falcon.HTTP_404
				return

			session.delete(article)
			session.commit()
			req.context['result'] = {}
		except:
			session.rollback()
			raise
		finally:
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
		resources = [ util.content.dir_to_json(inst.resource) for inst in data if inst.resource is not None ] if user.is_org() else []

		req.context['result'] = {
			'articles': articles,
			'meta': { 'total': count },
			'contents': resources
		}

	# Pridani noveho clanku
	def on_post(self, req, resp):
		user = req.context['user']
		if (not user.is_logged_in()) or (not user.is_org()):
			req.context['result'] = { 'errors': [ { 'status': '401', 'title': 'Unauthorized', 'detail': u'Přidat článek může pouze organizátor.' } ] }
			resp.status = falcon.HTTP_400
			return

		data = json.loads(req.stream.read())['article']

		try:
			article = model.Article(
				author = user.id,
				title = data['title'],
				body = data['body'],
				published = data['published'],
				year = req.context['year'],
				time_created = dateutil.parser.parse(data['time_published']),
				picture = data['picture']
			)

			session.add(article)
			session.commit()

			article.resource = 'articles/' + str(article.id)
			session.commit()
		except:
			session.rollback()
			raise

		req.context['result'] = { 'article': _artice_to_json(article) }

		session.close()

