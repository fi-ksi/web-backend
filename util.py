
def fake_auth(req, resp):
		resp.set_header('Access-Control-Allow-Credentials', 'true')
		resp.set_header('Access-Control-Allow-Headers', 'content-type')
		resp.set_header('Access-Control-Allow-Methods', 'GET,HEAD,PUT,PATCH,POST,DELETE')
