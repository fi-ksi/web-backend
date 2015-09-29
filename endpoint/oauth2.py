import falcon

from db import session
import auth
import model

class Error:
	INVALID_REQUEST = 'invalid_request'
	UNAUTHORIZED_CLIENT = 'unauthorized_client'

class Authorize(object):

	def _auth(self, req, resp):
		username = req.get_param('username')
		password = req.get_param('password')

		challenge = session.query(model.User).filter(
			model.User.email == username,
			model.User.password == password).first()

		if challenge:
			req.context['result'] = auth.OAuth2Token(challenge.id).data
		else:
			req.context['result'] = {'error': Error.UNAUTHORIZED_CLIENT}
			resp.status = falcon.HTTP_400

	def _refresh(self, req, resp):
		refresh_token = req.get_param('refresh_token')

		token = session.query(model.Token).filter(
			model.Token.refresh_token == refresh_token).first()

		if token:
			session.delete(token)
			req.context['result'] = auth.OAuth2Token(token.user).data
		else:
			req.context['result'] = {'error': Error.UNAUTHORIZED_CLIENT}
			resp.status = falcon.HTTP_400

	def on_post(self, req, resp):
		grant_type = req.get_param('grant_type')

		if grant_type == 'password':
			self._auth(req, resp)
		elif grant_type == 'refresh_token':
			self._refresh(req, resp)
		else:
			resp.status = falcon.HTTP_400
