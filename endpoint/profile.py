import json
import falcon
import magic
import tempfile
import os
from sqlalchemy import func
from PIL import Image
from sqlalchemy.exc import SQLAlchemyError
import multipart

from db import session
import model
import util


UPLOAD_DIR = os.path.join('data', 'images', 'profile')
ALLOWED_MIME_TYPES = {
    'image/jpeg': 'jpg',
    'image/pjpeg': 'jpg',
    'image/png': 'png',
    'image/gif': 'gif'
}
THUMB_SIZE = (263, 263)


class Profile(object):

    def on_put(self, req, resp):
        try:
            userinfo = req.context['user']

            if not userinfo.is_logged_in():
                resp.status = falcon.HTTP_400
                return

            data = json.loads(req.stream.read().decode('utf-8'))
            user, profile, notify = session.query(model.User).\
                filter(model.User.id == userinfo.get_id()).\
                outerjoin(model.Profile,
                          model.User.id == model.Profile.user_id).\
                add_entity(model.Profile).\
                outerjoin(model.UserNotify,
                          model.User.id == model.UserNotify.user).\
                add_entity(model.UserNotify).\
                first()

            user.first_name = data['first_name']
            user.nick_name = data['nick_name']
            user.last_name = data['last_name']
            user.email = data['email']
            user.sex = data['gender']
            user.short_info = data['short_info']
            user.github = data['github']

            profile.addr_street = data['addr_street']
            profile.addr_city = data['addr_city']
            profile.addr_zip = data['addr_zip']
            profile.addr_country = data['addr_country'].lower()
            profile.school_name = data['school_name']
            profile.school_street = data['school_street']
            profile.school_city = data['school_city']
            profile.school_zip = data['school_zip']
            profile.school_country = data['school_country'].lower()
            profile.school_finish = data['school_finish']
            profile.tshirt_size = data['tshirt_size']

            if notify is None:
                notify = model.UserNotify(
                    user=userinfo.get_id(),
                    auth_token=util.user_notify.new_token(),
                )
            notify.notify_eval = data['notify_eval'] if 'notify_eval' in data else True
            notify.notify_response = data['notify_response'] if 'notify_response' in data else True
            notify.notify_ksi = data['notify_ksi'] if 'notify_ksi' in data else True
            notify.notify_events = data['notify_events'] if 'notify_events' in data else True

            session.add(user)
            session.add(profile)
            session.add(notify)
            session.commit()

            req.context['result'] = util.profile.to_json(
                user, profile, notify,
                req.context['year_obj']
            )
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()

    def on_get(self, req, resp):
        try:
            userinfo = req.context['user']

            if not userinfo.is_logged_in():
                req.context['result'] = util.profile.fake_profile()
                return

            profile = session.query(model.Profile).get(userinfo.id)
            notify = session.query(model.UserNotify).get(userinfo.id)
            req.context['result'] = util.profile.to_json(
                userinfo.user, profile, notify, req.context['year_obj'],
                basic=False,
                sensitive=True
            )
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()


# Basic profile
class BasicProfile(object):

    def on_get(self, req, resp):
        try:
            userinfo = req.context['user']

            if not userinfo.is_logged_in():
                req.context['result'] = util.profile.fake_profile()
                return

            profile = session.query(model.Profile).get(userinfo.id)
            notify = session.query(model.UserNotify).get(userinfo.id)
            req.context['result'] = {
                'basicProfile': util.profile.to_json(
                    userinfo.user, profile, notify, req.context['year_obj'],
                    basic=True
                )['profile']
            }
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()


# Profily lidi vydavame jen adminum.
class OrgProfile(object):

    def on_get(self, req, resp, id):
        try:
            userinfo = req.context['user']

            if (not userinfo.is_logged_in()) or (not userinfo.is_org()):
                req.context['result'] = {
                    'errors': [{
                        'status': '401',
                        'title': 'Unauthorized',
                        'detail': ('Prohlížet cizí profily může pouze '
                                   'administrátor.')
                    }]
                }
                resp.status = falcon.HTTP_400
                return

            user = session.query(model.User).get(id)
            profile = session.query(model.Profile).get(id)

            if (not user) or (not profile):
                req.context['result'] = {
                    'errors': [{
                        'status': '404',
                        'title': 'Not Found',
                        'detail': 'Uživatel nebo profil s tímto ID neexistuje.'
                    }]
                }
                resp.status = falcon.HTTP_404
                return

            notify = session.query(model.UserNotify).get(userinfo.id)
            req.context['result'] = util.profile.to_json(
                user,
                profile,
                notify,
                req.context['year_obj'],
                sensitive=userinfo.is_admin()
            )
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()


class PictureUploader(object):

    def _crop(self, src, dest):
        img = Image.open(src)
        width, height = img.size

        if width > height:
            delta = width - height
            left = int(delta / 2)
            upper = 0
            right = height + left
            lower = height
        else:
            delta = height - width
            left = 0
            upper = int(delta / 2)
            right = width
            lower = width + upper

        img = img.crop((left, upper, right, lower))
        img.thumbnail(THUMB_SIZE, Image.ANTIALIAS)
        img.save(dest)

    def on_post(self, req, resp):
        try:
            userinfo = req.context['user']

            if not userinfo.is_logged_in():
                resp.status = falcon.HTTP_400
                return

            user = session.query(model.User).\
                filter(model.User.id == userinfo.get_id()).\
                first()

            files = multipart.MultiDict()
            content_type, options = multipart.parse_options_header(
                req.content_type
            )
            boundary = options.get('boundary', '')

            if not boundary:
                raise multipart.MultipartError("No boundary for "
                                               "multipart/form-data.")

            for part in multipart.MultipartParser(req.stream, boundary,
                                                  req.content_length):
                files[part.name] = part

            file = files.get('file')
            user_id = req.context['user'].get_id()
            tmpfile = tempfile.NamedTemporaryFile(delete=False)

            file.save_as(tmpfile.name)

            mime = magic.Magic(mime=True).from_file(tmpfile.name)

            if mime not in ALLOWED_MIME_TYPES:
                resp.status = falcon.HTTP_400
                return

            if not os.path.isdir(UPLOAD_DIR):
                try:
                    os.makedirs(UPLOAD_DIR)
                except OSError:
                    print('Unable to create directory for profile pictures')
                    resp.status = falcon.HTTP_500
                    return

            new_picture = os.path.join(UPLOAD_DIR, 'user_%d.%s' % (
                user_id, ALLOWED_MIME_TYPES[mime]
            ))

            self._crop(tmpfile.name, new_picture)
            try:
                os.remove(tmpfile.name)
            except OSError:
                print('Unable to remove temporary file %s' % tmpfile.name)

            user.profile_picture = new_picture
            session.commit()

            req.context['result'] = {}
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()
