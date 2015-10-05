import json, falcon, magic, tempfile, shutil, Image, os
from sqlalchemy import func

from db import session
import model
import util
import multipart

ALLOWED_MIME_TYPES = { 'image/jpeg': 'jpg', 'image/pjpeg': 'jpg', 'image/png': 'png', 'image/gif': 'gif' }
THUMB_SIZE = 263, 263

class Profile(object):

	#TODO: Realne ukladani dat
	def on_put(self, req, resp):
		userinfo = req.context['user']

		if not userinfo.is_logged_in():
			resp.status = falcon.HTTP_400
			return

		data = json.loads(req.stream.read())
		user, profile = session.query(model.User).filter(model.User.id == userinfo.get_id()).outerjoin(model.Profile, model.User.id == model.Profile.user_id).add_entity(model.Profile).first()

		user.first_name = data['first_name']
		user.last_name = data['last_name']
		user.email = data['email']

		profile.short_info = data['short_info']
		profile.addr_street = data['addr_street']
		profile.addr_city = data['addr_city']
		profile.addr_zip = data['addr_zip']
		profile.addr_country = data['addr_country']
		profile.school_name = data['school_name']
		profile.school_street = data['school_street']
		profile.school_city = data['school_city']
		profile.school_zip = data['school_zip']
		profile.school_country = data['school_country']
		profile.school_finish = data['school_finish']
		profile.tshirt_size = data['tshirt_size']

		session.add(user)
		session.add(profile)
		session.commit()

		req.context['result'] = util.profile.to_json(user, profile)
		session.close()


	def on_get(self, req, resp):
		userinfo = req.context['user']

		if not userinfo.is_logged_in():
			req.context['result'] = util.profile.fake_profile()
			return

		user, profile = session.query(model.User).filter(model.User.id == userinfo.get_id()).outerjoin(model.Profile, model.User.id == model.Profile.user_id).add_entity(model.Profile).first()

		req.context['result'] = util.profile.to_json(user, profile)

class PictureUploader(object):

	def _crop(self, src, dest):
		img = Image.open(src)
		width, height = img.size

		if width > height:
			delta = width - height
			left = int(delta/2)
			upper = 0
			right = height + left
			lower = height
		else:
			delta = height - width
			left = 0
			upper = int(delta/2)
			right = width
			lower = width + upper

		img = img.crop((left, upper, right, lower))
		img.thumbnail(THUMB_SIZE, Image.ANTIALIAS)
		img.save(dest)

	def on_post(self, req, resp):
		userinfo = req.context['user']

		if not userinfo.is_logged_in():
			resp.status = falcon.HTTP_400
			return

		user = session.query(model.User).filter(model.User.id == userinfo.get_id()).first()

		files = multipart.MultiDict()
		content_type, options = multipart.parse_options_header(req.content_type)
		boundary = options.get('boundary','')

		if not boundary:
			raise multipart.MultipartError("No boundary for multipart/form-data.")

		for part in multipart.MultipartParser(req.stream, boundary, req.content_length):
			files[part.name] = part

		file = files.get('file')
		user_id = req.context['user'].get_id()
		tmpfile = tempfile.NamedTemporaryFile(delete = False)

		file.save_as(tmpfile.name)

		mime = magic.Magic(mime=True).from_file(tmpfile.name)

		if mime not in ALLOWED_MIME_TYPES:
			resp.status = falcon.HTTP_400
			return

		new_picture = 'images/profile/user_%d.%s' % (user_id, ALLOWED_MIME_TYPES[mime])

		self._crop(tmpfile.name, new_picture)
		os.remove(tmpfile.name)

		if user.profile_picture:
			os.remove(user.profile_picture)

		user.profile_picture = new_picture

		session.add(user)
		session.commit()
		session.close()
