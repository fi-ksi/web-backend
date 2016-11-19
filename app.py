# -*- coding: utf-8 -*-

import falcon, json, sys
from datetime import datetime, timedelta

import copy
import model
import endpoint
from db import engine, session
from util import UserInfo
from sqlalchemy import func, desc
from sqlalchemy.exc import SQLAlchemyError

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
			try:
				token = session.query(model.Token).get(token_str)

				if token is not None:
					if req.relative_uri != '/auth' and token.expire < datetime.utcnow():
						# user timeouted
						req.context['user'] = UserInfo()
						return

					try:
						req.context['user'] = UserInfo(session.query(model.User).get(token.user), token_str)
						return
					except AttributeError:
						pass
			except:
				session.rollback()
				raise

		req.context['user'] = UserInfo()

class Year_fill(object):

	# This middleware has 2 purposes:
	#  1) Get current year.
	#  2) Test connection with db. (this is very important!)
	def process_request(self, req, resp):
		if req.method == 'OPTIONS': return
		try:
			if ('YEAR' in req.headers):
				req.context['year'] = req.headers['YEAR']
				req.context['year_obj'] = session.query(model.Year).get(req.context['year'])
			else:
				year_obj = session.query(model.Year).order_by(desc(model.Year.id)).first()
				req.context['year_obj'] = year_obj
				req.context['year'] = year_obj.id
		except SQLAlchemyError:
			session.rollback()
			try:
				if ('YEAR' in req.headers):
					req.context['year'] = req.headers['YEAR']
					req.context['year_obj'] = session.query(model.Year).get(req.context['year'])
				else:
					year_obj = session.query(model.Year).order_by(desc(model.Year.id)).first()
					req.context['year_obj'] = year_obj
					req.context['year'] = year_obj.id
			except:
				session.rollback()
				raise

def log(req, resp):
	try:
		ip = req.env['HTTP_X_FORWARDED_FOR'].split(',')[-1].strip()
	except KeyError:
		ip = req.env['REMOTE_ADDR']

	print '[%s] [%s] [%s] [%s] %s' % (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), ip, req.method, resp.status, req.relative_uri)
	sys.stdout.flush()

class Logger(object):

	def process_request(self, req, resp):
		log(req, resp)

def log_sink(req, resp):
	resp.status = falcon.HTTP_404

	# Uncomment this to log sink
	#log(req, resp)

class Corser(object):

	def process_response(self, request, response, resource):
		origin = request.get_header('Origin')

		if origin in (	'http://localhost:4200',
				'https://ksi.fi.muni.cz',
				'https://kyzikos.fi.muni.cz'):
			response.set_header('Access-Control-Allow-Origin', origin)

		response.set_header('Access-Control-Allow-Headers', 'authorization,content-type,year')
		response.set_header('Access-Control-Allow-Methods', 'OPTIONS,PUT,POST,GET,DELETE')


# Add Logger() to middleware for logging
api = falcon.API(middleware=[JSONTranslator(), Authorizer(), Year_fill(), Corser()])


# Odkomentovat pro vytvoreni tabulek v databazi
#model.Base.metadata.create_all(engine)

api.add_route('/robots.txt', endpoint.Robots())
api.add_route('/csp', endpoint.CSP())
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
api.add_route('/profile/picture', endpoint.PictureUploader())
api.add_route('/profile/{id}', endpoint.OrgProfile())
api.add_route('/profile/', endpoint.Profile())
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


api.add_route('/admin/evaluations/{id}', endpoint.admin.Evaluation())
api.add_route('/admin/corrections', endpoint.admin.Corrections())
api.add_route('/admin/corrections/{id}', endpoint.admin.Correction())
api.add_route('/admin/correctionsInfos', endpoint.admin.CorrectionsInfo())
api.add_route('/admin/correctionsInfos/{id}', endpoint.admin.CorrectionInfo())
api.add_route('/admin/correctionsEmail/{id}', endpoint.admin.CorrectionsEmail())
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
api.add_route('/admin/user-export', endpoint.admin.UserExport())
api.add_route('/admin/evalCodes/{id}', endpoint.admin.EvalCode())

api.add_sink(log_sink)
