# -*- coding: utf-8 -*-

import os, time, uuid, magic, multipart

import falcon

from db import session
import model
import util

class Content(object):

	# Smaze adresarovou strukturu rekurzivne od nejvic zanoreneho
	#  dokud jsou adresare prazdne.
	def _delete_tree(self, path):
		if os.listdir(path) != []: return
		try:
			os.rmdir(path)
			_delete_tree(os.path.dirname(path))
		except:
			return

	# GET na content vraci
	# a) soubor, pokud je v \path cesta k souboru,
	# b) obsah adresare, pokud je v \path cesta k adresari.
	def on_get(self, req, resp):
		if req.get_param('path'):
			shortPath = req.get_param('path').replace('..', '')
		else:
			shortPath = "."
		filePath = 'data/content/' + shortPath

		if os.path.isdir(filePath):
			req.context['result'] = { 'content': util.content.dir_to_json(shortPath) }
			return

		if not os.path.isfile(filePath):
			req.context['result'] = { 'content': util.content.empty_content(shortPath) }
			return

		resp.content_type = magic.Magic(mime=True).from_file(filePath)
		resp.stream_len = os.path.getsize(filePath)
		resp.stream = open(filePath, 'rb')

	def on_post(self, req, resp):
		user = req.context['user']

		if (not user.is_logged_in()) or (not user.is_org()):
			req.context['result'] = { 'errors': [ { 'status': '401', 'title': 'Unauthorized', 'detail': u'Upravovat content může pouze organizátor.' } ] }
			resp.status = falcon.HTTP_400
			return

		if req.get_param('path'):
			shortPath = req.get_param('path').replace('..', '')
		else:
			shortPath = "."
		dirPath = 'data/content/' + shortPath

		if not req.content_length:
			resp.status = falcon.HTTP_411
			return

		if req.content_length > util.config.MAX_UPLOAD_FILE_SIZE:
			resp.status = falcon.HTTP_413
			return

		files = multipart.MultiDict()
		content_type, options = multipart.parse_options_header(req.content_type)
		boundary = options.get('boundary', '')

		if not boundary:
			raise multipart.MultipartError("No boundary for multipart/form-data.")

		try:
			if not os.path.isdir(dirPath): os.makedirs(dirPath)

			for part in multipart.MultipartParser(req.stream, boundary, req.content_length, 2**30, 2**20, 2**18, 2**16, 'utf-8'):
				path = '%s/%s' % (dirPath, part.filename)
				part.save_as(path)
		except:
			resp.status = falcon.HTTP_500
			raise

		req.context['result'] = {}
		resp.status = falcon.HTTP_200

	def on_delete(self, req, resp):
		user = req.context['user']

		if (not user.is_logged_in()) or (not user.is_org()):
			resp.status = falcon.HTTP_400
			return

		if req.get_param('path'):
			shortPath = req.get_param('path').replace('..', '')
		else:
			shortPath = "."
		filePath = 'data/content/' + shortPath

		if not os.path.isfile(filePath):
			resp.status = falcon.HTTP_404
			return

		try:
			os.remove(filePath)
			self._delete_tree(os.path.dirname(filePath))
		except:
			resp.status = falcon.HTTP_500
			raise

		resp.status = falcon.HTTP_200
		req.context['result'] = {}


class TaskContent(object):

	def on_get(self, req, resp, id, view):
		user = req.context['user']

		if not view in ['zadani', 'reseni', 'icon']:
			resp.status = falcon.HTTP_400
			return

		filePath = 'data/task-content/' + id + '/' + view + '/' + req.get_param('path').replace('..', '')

		if not os.path.isfile(filePath):
			resp.status = falcon.HTTP_404
			return

		resp.content_type = magic.Magic(mime=True).from_file(filePath)
		resp.stream_len = os.path.getsize(filePath)
		resp.stream = open(filePath, 'rb')
