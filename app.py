import falcon, json
from datetime import datetime, timedelta

import copy
import model
import endpoint
from db import engine, session
from util import UserInfo
from sqlalchemy import func

# Cache aktualniho rocniku
c_year = None
c_year_update = None

###############################################################################

class JSONTranslator(object):

	def process_request(self, req, resp):
		return

	def process_response(self, req, resp, endpoint):
		if 'result' not in req.context:
			return

		resp.body = json.dumps(req.context['result'], sort_keys=True, indent=4)


class Authorizer(object):

	def process_request(self, req, resp):
		if req.auth:
			token_str = req.auth.split(' ')[-1]
			token = session.query(model.Token).get(token_str)

			if token is not None:
				if req.relative_uri != '/auth' and token.granted + token.expire < datetime.utcnow():
					raise falcon.HTTPError(falcon.HTTP_401)

				try:
					req.context['user'] = UserInfo(session.query(model.User).get(token.user), token_str)
					return
				except AttributeError:
					pass

		req.context['user'] = UserInfo()

class Year_fill(object):

	def process_request(self, req, resp):
		global c_year
		global c_year_update

		if ('YEAR' in req.headers):
			req.context['year'] = req.headers['YEAR']
		else:
			if (c_year is None) or (c_year_update is None) or (c_year_update < datetime.utcnow()):
				try:
					c_year = session.query(func.max(model.Year.id)).scalar()
				except:
					session.rollback()
					try:
						c_year = session.query(func.max(model.Year.id)).scalar()
					except:
						session.rollback()
						raise
				c_year_update = copy.copy(datetime.utcnow()) + timedelta(minutes=30)
			req.context['year'] = c_year

def log(req, resp):
	try:
		ip = req.env['HTTP_X_FORWARDED_FOR'].split(',')[-1].strip()
	except KeyError:
		ip = req.env['REMOTE_ADDR']

	print '[%s] [%s] [%s] [%s] %s' % (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), ip, req.method, resp.status, req.relative_uri)

def log_middleware(req, resp, params):
	log(req, resp)

def log_sink(req, resp):
	resp.status = falcon.HTTP_404

	log(req, resp)

def cors_middleware(request, response, params):
	origin = request.get_header('Origin')

	if origin in (	'http://localhost:4200',
			'http://ksi.fi.muni.cz',
			'https://ksi.fi.muni.cz',
			'https://kyzikos.fi.muni.cz'):
						response.set_header('Access-Control-Allow-Origin', origin)

	response.set_header('Access-Control-Allow-Headers', 'authorization,content-type')
	response.set_header('Access-Control-Allow-Methods', 'OPTIONS,PUT,POST,GET,DELETE')


api = falcon.API(before=[ cors_middleware ], after=[ log_middleware ],
				 middleware=[JSONTranslator(), Authorizer(), Year_fill()])


model.Base.metadata.create_all(engine)

api.add_route('/articles', endpoint.Articles())
api.add_route('/articles/{id}', endpoint.Article())
api.add_route('/achievements', endpoint.Achievements())
api.add_route('/achievements/{id}', endpoint.Achievement())
api.add_route('/posts', endpoint.Posts())
api.add_route('/posts/{id}', endpoint.Post())
api.add_route('/tasks', endpoint.Tasks())
api.add_route('/tasks/{id}', endpoint.Task())
api.add_route('/taskDetails/{id}', endpoint.TaskDetails())
api.add_route('/modules/{id}', endpoint.Module())
api.add_route('/modules/{id}/submit', endpoint.ModuleSubmit())
api.add_route('/submFiles/{id}', endpoint.ModuleSubmittedFile())
api.add_route('/threads', endpoint.Threads())
api.add_route('/threads/{id}', endpoint.Thread())
api.add_route('/threadDetails/{id}', endpoint.ThreadDetails())
api.add_route('/users', endpoint.Users())
api.add_route('/users/{id}', endpoint.User())
api.add_route('/profile', endpoint.Profile())
api.add_route('/profile/picture', endpoint.PictureUploader())
api.add_route('/images/{context}/{id}', endpoint.Image())
api.add_route('/content', endpoint.Content())
api.add_route('/taskContent/{id}', endpoint.TaskContent())
	# This endpoint contains: (defined in endpoint/content.py, see also ./gunicorn_cfg.py)
		# /taskContent/{id}/zadani/{file_path}
		# /taskContent/{id}/reseni/{file_path}
		# /taskContent/[id]/icon/{file_name}
api.add_route('/task-content/{id}/{view}', endpoint.TaskContent())
api.add_route('/registration', endpoint.Registration())
api.add_route('/auth', endpoint.Authorize())
api.add_route('/logout', endpoint.Logout())
api.add_route('/runCode/{id}/submit', endpoint.RunCode())
api.add_route('/feedback', endpoint.Feedback())
api.add_route('/settings/changePassword', endpoint.ChangePassword())
api.add_route('/forgottenPassword', endpoint.ForgottenPassword())
api.add_route('/waves', endpoint.Waves())
api.add_route('/waves/{id}', endpoint.Wave())
api.add_route('/years', endpoint.Years())
api.add_route('/years/{id}', endpoint.Year())


api.add_route('/admin/corrections', endpoint.admin.Corrections())
api.add_route('/admin/corrections/{id}', endpoint.admin.Correction())
api.add_route('/admin/correctionsInfos', endpoint.admin.CorrectionsInfo())
api.add_route('/admin/corrections/{id}/publish', endpoint.admin.CorrectionsPublish())
api.add_route('/admin/subm/eval/{eval_id}/', endpoint.admin.SubmFilesEval())
api.add_route('/admin/subm/task/{task_id}/', endpoint.admin.SubmFilesTask())
api.add_route('/admin/e-mail/', endpoint.admin.Email())
api.add_route('/admin/atasks/', endpoint.admin.Tasks())
api.add_route('/admin/atasks/{id}', endpoint.admin.Task())
api.add_route('/admin/atasks/{id}/deploy', endpoint.admin.TaskDeploy())
api.add_route('/admin/atasks/{id}/merge', endpoint.admin.TaskMerge())
api.add_route('/admin/waves/{id}/diff', endpoint.admin.WaveDiff())
api.add_route('/admin/achievements/grant', endpoint.admin.AchievementGrant())

api.add_sink(log_sink)
