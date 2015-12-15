import os, time, uuid, magic

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
		filePath = 'data/content/' + req.get_param('path').replace('..', '');

		if os.path.isdir(filePath):
			req.context['result'] = util.content.dir_to_json(filePath)
			return

		if not os.path.isfile(filePath):
			resp.status = falcon.HTTP_404
			return

		resp.content_type = magic.Magic(mime=True).from_file(filePath)
		resp.stream_len = os.path.getsize(filePath)
		resp.stream = open(filePath, 'rb')

	def on_post(self, req, resp):
		user = req.context['user']

		if (not user.is_logged_in()) or (not user.is_org()):
			resp.status = falcon.HTTP_400
			return

		filePath = 'data/content/' + req.get_param('path').replace('..', '');

		if not req.content_length:
			resp.status = falcon.HTTP_411
			return

		if req.content_length > util.config.MAX_UPLOAD_FILE_SIZE:
			resp.status = falcon.HTTP_413
			return

		if os.path.isdir(filePath):
			resp.status = falcon.HTTP_409
			return

		try:
			if not os.path.isdir(os.path.dirname(filePath)):
				os.makedirs(os.path.dirname(filePath))

			with open(filePath, 'w') as f:
				f.write(req.stream.read())
		except:
			resp.status = falcon.HTTP_500
			raise

		resp.status = falcon.HTTP_200

	def on_delete(self, req, resp):
		user = req.context['user']

		if (not user.is_logged_in()) or (not user.is_org()):
			resp.status = falcon.HTTP_400
			return

		filePath = 'data/content/' + req.get_param('path').replace('..', '');

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
