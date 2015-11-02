bind='127.0.0.1:3030'
pidfile='gunicorn_pid'
daemon=True
errorlog='gunicorn_error.log'
workers=4

def pre_request(worker, req):
	if req.path.startswith('/content/'):
		req.query = 'path=' + req.path[9:]
		req.path = '/content'
