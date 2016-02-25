from db import session
import model, os, falcon

class EvalCode(object):

	def on_get(self, req, resp, id):
		user = req.context['user']

		if (not user.is_logged_in()) or (not user.is_org()):
			resp.status = falcon.HTTP_400
			return

		code = session.query(model.SubmittedCode).\
			filter(model.SubmittedCode.evaluation == id).first()

		if not code:
			req.context['result'] = { 'errors': [ { 'id': 5, 'title': "Code not found in db" } ] }
			return

		evaluation = session.query(model.Evaluation).get(code.evaluation)
		if not evaluation:
			req.context['result'] = { 'errors': [ { 'id': 5, 'title': "Evaluation not found in db" } ] }
			return

		eval_dir = 'data/submissions/module_' + str(evaluation.module) + '/' + 'user_' + str(evaluation.user) + '/'

		try:
			req.context['result'] = {
				'evalCode': {
					'id': evaluation.id,
					'code': code.code,
					'merged': open(eval_dir+'sandbox/code.py', 'r').read() if os.path.isfile(eval_dir+'sandbox/code.py') else "Soubor "+eval_dir+'sandbox/code.py'+" neexistuje",
					'stdout': open(eval_dir+'sandbox.stdout').read() if os.path.isfile(eval_dir+'sandbox.stdout') else "Soubor "+eval_dir+'sandbox.stdout'+" neexistuje",
					'stderr': open(eval_dir+'sandbox.stderr').read() if os.path.isfile(eval_dir+'sandbox.stderr') else "Soubor "+eval_dir+'sandbox.stderr'+" neexistuje",
					'merge_stdout': open(eval_dir+'merge.stdout').read() if os.path.isfile(eval_dir+'merge.stdout') else "Soubor "+eval_dir+'merge.stdout'+" neexistuje",
					'check_stdout': open(eval_dir+'check.stdout').read() if os.path.isfile(eval_dir+'check.stdout') else "Soubor "+eval_dir+'check.stdout'+" neexistuje",
				}
			}
		except Exception as e:
			req.context['result'] = { 'errors': [ { 'id': 10, 'title': str(e) } ] }

